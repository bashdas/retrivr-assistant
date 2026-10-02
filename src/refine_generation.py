"""Replay frozen baseline contexts to isolate the observed duration-unit error."""
import argparse
import copy
import json
from pathlib import Path

from dotenv import load_dotenv
from langchain_core.documents import Document
from langchain_openai import ChatOpenAI

from capstone_compare import STRICT_PROMPT, answer_with_retriever, collection_failure_answer
from collect_api import dump


def main():
    load_dotenv(Path(__file__).resolve().parents[1] / '.env', override=True)
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--baseline', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--guard-only', action='store_true', help='Apply collection guard to saved answers; zero model calls')
    args = parser.parse_args()
    if args.output.exists():
        parser.error('output exists; preserve previous results')
    original = json.loads(args.baseline.read_text())
    result = copy.deepcopy(original)
    result['prompt_policy'] = 'separate-messages-duration-unit-v2+collection-guard'
    result['prompt_text'] = STRICT_PROMPT
    result['baseline_source'] = str(args.baseline)
    if 'baseline' in result:
        result['generation_refined'] = result.pop('baseline')
    result['generation_refined']['name'] = 'Baseline retrieval + strict duration prompt'
    rows = result['generation_refined']['rows']
    print(f'Frozen contexts: {len(rows)}; new embeddings: 0; LLM calls at most: {0 if args.guard_only else len(rows)}', flush=True)
    llm = None if args.guard_only else ChatOpenAI(model=result['config']['model'], temperature=0, max_retries=0)
    for row in rows:
        documents = [Document(page_content=d['content'], metadata=d['metadata']) for d in row['retrieved']]
        if args.guard_only:
            guarded = collection_failure_answer(row['question'], documents)
            if guarded:
                row['answer'] = guarded
            row['answer_origin'] = 'collection_guard' if guarded else 'saved_model_answer'
        else:
            row['answer'] = answer_with_retriever(row['question'], documents, llm, STRICT_PROMPT)
        row['generation_review'] = dict(grounded=None, direct=None, abstains_if_unanswerable=None, notes='')
        print(f'{row["id"]}: generated', flush=True)
    dump(args.output, result)


if __name__ == '__main__':
    main()
