"""Deterministic API fixtures; uses the real collector without any network calls."""
import argparse
from pathlib import Path
from collect_api import CollectionError, collect, dump

ORGS = [
    (101, '가상누리대학교 컴퓨터공학과'),
    (102, '가상누리대학교 총학생회'),
    (103, '가상한빛대학교 사진동아리'),
    (104, '가상한빛대학교 체육학과'),
    (105, '가상누리대학교 수집실패동아리'),
]
NAMES = ['노트북 거치대', '축구공', '무선 마이크 RX-7', '보조배터리 PB-20000', '카메라 삼각대', '우산']


class MockClient:
    base = 'https://mock.retrivr.invalid'
    data_kind = 'mock'

    def __init__(self):
        self.calls = 0
        self.orgs = dict(ORGS)
        self.items, self.details = {}, {}
        for oid, org in ORGS[:-1]:
            rows = []
            for index, name in enumerate(NAMES, 1):
                iid = oid * 100 + index
                row = dict(itemId=iid, name=name, availableQuantity=(oid+index) % 5,
                           totalQuantity=6, isActive=True, rentalDuration=3+index,
                           description=f'{org}에서 관리하는 {name}. 가상 실험 자료.', guaranteedGoods='학생증')
                detail = dict(itemManagementType='UNIT', level='FREE',
                              borrowerRequirements=[{'label':'학번', 'required':True}, {'label':'연락처', 'required':False}],
                              itemUnits=[{'itemUnitId':iid*10+j, 'label':f'{name} {j}', 'status':status}
                                         for j,status in enumerate(['AVAILABLE','RENTAL_PENDING','RENTED','LOST','BROKEN','INACTIVE'],1)])
                row['availableQuantity'] = 1
                if index == 1:
                    detail['itemManagementType'] = 'NON_UNIT'
                    detail['itemUnits'] = []
                    row['availableQuantity'] = 4 if oid == 101 else 2
                if oid == 101 and index == 3:
                    row['description'] += ' 코드 RX-7. 행사 진행자의 목소리를 스피커로 전달하는 휴대용 음성 장비.'
                    row['guaranteedGoods'] = '학생증과 보증금 10000원'
                if oid == 103 and index == 5:
                    row['description'] += ' 야간 장노출 사진 촬영 시 카메라 흔들림을 줄이는 지지대.'
                if oid == 102 and index == 4:
                    row['isActive'] = False
                    row['availableQuantity'] = 0
                    detail['itemUnits'] = [dict(u, status='INACTIVE') for u in detail['itemUnits']]
                if oid == 104 and index == 6:
                    row['guaranteedGoods'] = None
                rows.append(row)
                self.details[iid] = detail
            self.items[oid] = rows

    def get(self, path, params=None):
        self.calls += 1
        params = params or {}
        if path.endswith('/search'):
            start = 2 if params.get('cursor') == 'opaque-page-2' else 0
            if start:
                return {'organizations':[{'organizationId':oid,'name':name} for oid,name in ORGS[2:]], 'nextCursor':None}
            return {'organizations':[{'organizationId':oid,'name':name} for oid,name in ORGS[:2]], 'nextCursor':'opaque-page-2'}
        if path.endswith('/items'):
            oid = int(path.split('/')[-2])
            if oid == 105:
                raise CollectionError('http_503')
            start = 3 if params.get('cursor') is not None else 0
            return dict(organizationId=oid, organizationName=self.orgs[oid], items=self.items[oid][start:start+3],
                        nextCursor=self.items[oid][2]['itemId'] if not start else None)
        iid = int(path.split('/')[-1])
        if iid == 10406:
            raise CollectionError('http_503')
        return self.details[iid]


def cases():
    specs = [
        ('가상누리대학교 컴퓨터공학과 노트북 거치대는 몇 개 빌릴 수 있나요?', '대여 가능 수량: 4', 'org-101-item-10101'),
        ('가상누리대학교 총학생회 노트북 거치대는 몇 개 빌릴 수 있나요?', '대여 가능 수량: 2', 'org-102-item-10201'),
        ('가상누리대학교 컴퓨터공학과의 RX-7을 빌릴 때 맡기는 것은?', '담보 물품: "학생증과 보증금 10000원"', 'org-101-item-10103'),
        ('가상한빛대학교 사진동아리에서 야간 촬영할 때 카메라가 흔들리지 않게 받쳐주는 장비는?', '야간 장노출 사진 촬영', 'org-103-item-10305'),
        ('가상누리대학교 컴퓨터공학과 축구공의 분실·고장·승인 대기 상태를 알려주세요.', '"status": "BROKEN"', 'org-101-item-10102'),
        ('가상누리대학교 총학생회 PB-20000은 활성 상태인가요?', '활성 여부: false', 'org-102-item-10204'),
        ('가상누리대학교 컴퓨터공학과의 RX-7은 얼마나 오래 빌리나요?', '대여 기간(rentalDuration 원값): 6', 'org-101-item-10103'),
        ('가상한빛대학교 체육학과 우산 대여 시 필수 입력 정보를 알려주세요.', None, None),
        ('가상누리대학교 수집실패동아리는 물품이 하나도 없는 거죠?', None, None),
        ('제 소속 단체를 확인하고 내일 실시간 대여 가능한 전체 물품 수를 알려주세요.', None, None),
    ]
    return [dict(id=f'Q{i}',question=q,expected_keyword=gold,expected_doc_ids=[doc] if doc else [])
            for i,(q,gold,doc) in enumerate(specs,1)]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=Path('data/mock/experiment-v1'))
    parser.add_argument('--cases', type=Path, default=Path('results/mock-questions.json'))
    args = parser.parse_args()
    if args.cases.exists() or args.output.exists():
        parser.error('fixture output exists; use fresh paths to preserve fixed experiments')
    manifest = collect(MockClient(), ['가상누리대학교','가상한빛대학교'], args.output)
    dump(args.cases, cases())
    print(f'MOCK ONLY: {len(manifest["organizations"])} orgs, {len(manifest["documents"])} documents, {len(manifest["errors"])} intentional failures; network calls=0')


if __name__ == '__main__':
    main()
