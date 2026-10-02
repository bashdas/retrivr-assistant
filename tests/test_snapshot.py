"""Synthetic fixtures only: never claim these are service evaluation results."""
import sys
import tempfile
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from collect_api import CollectionError, collect, pages
from capstone_compare import load_snapshot, hit, Hybrid


class FakeClient:
    base = 'https://fixture.invalid'
    def __init__(self): self.calls = 0
    def get(self, path, params=None):
        self.calls += 1
        if path.endswith('/search'):
            return {'organizations': [{'organizationId': 1, 'name': '가상학교 테스트단체'}], 'nextCursor': None}
        if path.endswith('/items'):
            cursor = params.get('cursor')
            return {'organizationId': 1, 'organizationName': '가상학교 테스트단체',
                    'items': [{'itemId': 20 if cursor is None else 21, 'name': '가상물품', 'availableQuantity': 0,
                               'totalQuantity': 2, 'description': '긴 설명 ' * 500}],
                    'nextCursor': 20 if cursor is None else None}
        if path.endswith('/20'):
            return {'itemUnits': [{'itemUnitId': 1, 'label': 'A', 'status': 'BROKEN'}],
                    'borrowerRequirements': [], 'itemManagementType': 'UNIT', 'level': 'FREE'}
        raise CollectionError('http_503')


class SnapshotTests(unittest.TestCase):
    def test_collection_dedup_pagination_failure_and_chunk_identity(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / 'snapshot'
            manifest = collect(FakeClient(), ['가상', '학교'], root)
            self.assertEqual(len(manifest['organizations']), 1)
            self.assertEqual(manifest['organizations'][0]['collected_item_count'], 2)
            self.assertFalse(manifest['complete'])
            self.assertEqual(manifest['errors'][0]['stage'], 'detail')
            _, docs, chunks = load_snapshot(root)
            self.assertGreater(len(chunks), len(docs))
            for chunk in chunks:
                self.assertIn('단체 ID: 1', chunk.page_content)
                self.assertIn('수집 시각', chunk.page_content)
                self.assertIn('출처:', chunk.page_content)
                if chunk.metadata['item_id']:
                    self.assertIn(f'물품 ID: {chunk.metadata["item_id"]}', chunk.page_content)
            failed = next(d for d in docs if d.metadata['item_id'] == 21)
            self.assertIn('실패/확인 불가', failed.page_content)
            self.assertNotIn('물품 없음', failed.page_content)
            self.assertEqual(hit(chunks, '대여 가능 수량: 0', ['org-1-item-20']), 1)
            self.assertEqual(hit(chunks, '대여 가능 수량: 0', ['org-2-item-20']), 0)

    def test_cursor_types_and_repeat(self):
        class Client:
            def get(self, path, params): return {'organizations': [], 'nextCursor': 'opaque'}
        with self.assertRaisesRegex(CollectionError, 'repeated'):
            list(pages(Client(), '/', 'organizations', str))
        with self.assertRaisesRegex(CollectionError, 'invalid'):
            list(pages(Client(), '/', 'organizations', int))

    def test_failed_list_not_empty_inventory(self):
        class Failed(FakeClient):
            def get(self, path, params=None):
                if path.endswith('/items'): raise CollectionError('http_401')
                return super().get(path, params)
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / 'snapshot'
            result = collect(Failed(), ['가상'], root)
            self.assertFalse(result['organizations'][0]['list_complete'])
            text = (root / result['documents'][0]['file']).read_text()
            self.assertIn('물품 없음으로 해석할 수 없습니다', text)


if __name__ == '__main__': unittest.main()
