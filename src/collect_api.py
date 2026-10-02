"""Read-only public API snapshot collector. No credentials or response bodies in logs."""
import argparse
import json
import os
from datetime import datetime, timezone
from pathlib import Path

import requests
from dotenv import load_dotenv

DEFAULT_BASE = 'http://ec2-3-38-98-81.ap-northeast-2.compute.amazonaws.com'


def now():
    return datetime.now(timezone.utc).isoformat()


def dump(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding='utf-8')


class CollectionError(Exception):
    pass


class Client:
    def __init__(self, base, token='', max_requests=100):
        self.base = base.rstrip('/')
        self.session = requests.Session()
        if token:
            self.session.headers['Authorization'] = f'Bearer {token}'
        self.max_requests = max_requests
        self.calls = 0

    def get(self, path, params=None):
        if self.calls >= self.max_requests:
            raise CollectionError('request_budget_exceeded')
        self.calls += 1
        try:
            response = self.session.get(self.base + path, params=params, timeout=20, allow_redirects=False)
            if response.status_code != 200:
                raise CollectionError(f'http_{response.status_code}')
            data = response.json()
            if not isinstance(data, dict):
                raise CollectionError('invalid_response_object')
            return data
        except (requests.RequestException, ValueError):
            raise CollectionError('network_or_json_error') from None


def pages(client, path, field, cursor_type, params=None):
    params = dict(params or {}, size=15)
    seen = set()
    while True:
        data = client.get(path, params)
        if not isinstance(data.get(field), list) or 'nextCursor' not in data:
            raise CollectionError('invalid_page_schema')
        yield data
        cursor = data['nextCursor']
        if cursor is None:
            return
        if type(cursor) is not cursor_type or cursor in seen:
            raise CollectionError('invalid_or_repeated_cursor')
        seen.add(cursor)
        params['cursor'] = cursor


def identifier(value):
    if type(value) is not int or value < 1:
        raise CollectionError('invalid_id')
    return value


def display(value):
    if value is None:
        return '미제공/확인 불가'
    return json.dumps(value, ensure_ascii=False)


def collect(client, keywords, output):
    output.mkdir(parents=True, exist_ok=False)
    (output / 'documents').mkdir()
    data_kind = getattr(client, 'data_kind', 'real_api')
    manifest = dict(started_at=now(), keywords=keywords, data_kind=data_kind,
                    base_url=client.base, errors=[], documents=[], organizations=[])
    organizations = {}
    for keyword in keywords:
        try:
            for page in pages(client, '/api/public/v1/organizations/search', 'organizations', str, {'keyword': keyword}):
                for org in page['organizations']:
                    if not isinstance(org, dict):
                        raise CollectionError('invalid_organization_schema')
                    oid = identifier(org.get('organizationId'))
                    organizations[oid] = {'organizationId': oid, 'name': org.get('name')}
        except CollectionError as exc:
            manifest['errors'].append(dict(stage='search', keyword=keyword, error=str(exc)))
    for oid, org in organizations.items():
        path = f'/api/public/v1/organizations/{oid}/items'
        items, item_times, complete = {}, {}, False
        try:
            for page in pages(client, path, 'items', int):
                if page.get('organizationId') != oid:
                    raise CollectionError('organization_id_mismatch')
                org['name'] = page.get('organizationName') or org['name']
                for item in page['items']:
                    if not isinstance(item, dict):
                        raise CollectionError('invalid_item_schema')
                    iid = identifier(item.get('itemId'))
                    items[iid] = item
                    item_times[iid] = now()
            complete = True
        except CollectionError as exc:
            manifest['errors'].append(dict(stage='items', organization_id=oid, error=str(exc)))
        summary = dict(org, list_complete=complete, collected_item_count=len(items))
        manifest['organizations'].append(summary)
        records = [(None, None, None, None)]
        for iid, item in items.items():
            detail, error = None, None
            try:
                detail = client.get(f'/api/public/v1/items/{iid}')
                if not all(k in detail for k in ('itemUnits', 'borrowerRequirements', 'itemManagementType', 'level')):
                    raise CollectionError('invalid_detail_schema')
                if not isinstance(detail['itemUnits'], list) or not isinstance(detail['borrowerRequirements'], list):
                    raise CollectionError('invalid_detail_schema')
            except CollectionError as exc:
                detail, error = None, str(exc)
                manifest['errors'].append(dict(stage='detail', item_id=iid, error=error))
            records.append((item, detail, error, now()))
        for item, detail, error, detail_time in records:
            iid = item['itemId'] if item else None
            doc_id = f'org-{oid}' + (f'-item-{iid}' if item else '-catalog')
            collected_at = item_times[iid] if item else now()
            sources = [client.base + path]
            header = f'단체명: {org["name"]}\n단체 ID: {oid}\n수집 시각(UTC): {collected_at}\n'
            if data_kind == 'mock':
                header = '가상 MOCK 실험 데이터: 실제 단체·물품·수량이 아닙니다.\n' + header
            header += f'수집 키워드 범위: {", ".join(keywords)}\n실시간 상태가 아닌 수집 스냅샷입니다.\n'
            body = f'물품 목록 수집 완료: {complete}\n수집된 물품 수: {len(items)}\n'
            if item:
                header += f'물품명: {item.get("name")}\n물품 ID: {iid}\n'
                fields = {'availableQuantity':'대여 가능 수량', 'totalQuantity':'전체 수량', 'isActive':'활성 여부',
                          'rentalDuration':'대여 기간(rentalDuration 원값)', 'description':'설명', 'guaranteedGoods':'담보 물품'}
                body += '\n'.join(f'{label}: {display(item.get(key))}' for key, label in fields.items())
                body += f'\n상세 조회 시각(UTC): {detail_time}\n상세 수집 상태: {"성공" if detail is not None else "실패/확인 불가"}\n'
                if detail is not None:
                    body += '\n'.join(f'{k}: {display(detail[k])}' for k in ('itemManagementType','level','borrowerRequirements','itemUnits'))
                sources.append(client.base + f'/api/public/v1/items/{iid}')
            else:
                body += '수집된 목록: ' + display([{'itemId':i, 'name':v.get('name')} for i,v in items.items()])
                if not complete:
                    body += '\n수집 미완료: 물품 없음으로 해석할 수 없습니다.'
            body += '\n전체 수량과 대여 가능 수량의 차이는 모두 대여 중을 의미하지 않습니다.\n'
            header += '출처: ' + ' | '.join(sources) + '\n'
            relative = f'documents/{doc_id}.txt'
            (output / relative).write_text(header + '\n' + body, encoding='utf-8')
            manifest['documents'].append(dict(doc_id=doc_id, file=relative, organization_id=oid, item_id=iid,
                                              header=header, sources=sources, collected_at=collected_at))
    manifest.update(finished_at=now(), request_count=client.calls, complete=not manifest['errors'])
    dump(output / 'manifest.json', manifest)
    return manifest


def main():
    load_dotenv(Path(__file__).resolve().parents[1] / '.env', override=True)
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--keyword', action='append', required=True)
    parser.add_argument('--output', type=Path, required=True, help='New snapshot directory; never overwrites')
    parser.add_argument('--max-requests', type=int, default=100)
    parser.add_argument('--base-url', help='Explicit target; overrides .env for final production verification')
    args = parser.parse_args()
    keywords = list(dict.fromkeys(k.strip() for k in args.keyword if k.strip()))
    if not keywords or args.max_requests < 1:
        parser.error('nonempty keywords and positive request budget required')
    client = Client(args.base_url or os.getenv('RETRIVR_BASE_URL', DEFAULT_BASE), os.getenv('RETRIVR_API_TOKEN', ''), args.max_requests)
    manifest = collect(client, keywords, args.output)
    print(json.dumps({k: manifest[k] for k in ('request_count', 'complete')}, ensure_ascii=False))
    print(f'documents={len(manifest["documents"])} errors={len(manifest["errors"])}')
    return 0 if manifest['complete'] else 2


if __name__ == '__main__':
    raise SystemExit(main())
