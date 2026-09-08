"""Run with PYTHONPATH=shared:coptoc/api:sigtoc .venv/bin/python scripts/evaluate_intake.py.

Default validates the synthetic corpus without calling a provider. --live explicitly
runs configured API extraction and writes metrics to --output (default /tmp/intake-eval.json).
No database records are changed; keys are read from provider configuration, never printed.
"""
import argparse
import asyncio
import json
from pathlib import Path

from coptoc.ingestion import Manifest, EXTRACTION_INSTRUCTIONS
from sigtoc.work import model_structured, provider_config


def score(case, result):
    fields = {f.field:f.value for shipment in result.shipments for f in shipment.fields}
    correct = sum(fields.get(k) == v for k,v in case['expected'].items())
    forbidden = [k for k in case['forbidden_fields'] if k in fields]
    citations_valid = all(f.page == 1 and f.quote.strip() and f.quote in case['text'] for shipment in result.shipments for f in shipment.fields)
    clarification = bool(result.gaps or any(s.questions for s in result.shipments))
    return {'id':case['id'], 'expected_fields':len(case['expected']), 'correct_fields':correct,
            'missing_fields':[k for k in case['expected'] if k not in fields], 'forbidden_fields':forbidden,
            'citations_valid':citations_valid, 'required_clarification_present':not case['needs_clarification'] or clarification,
            'unsupported_input_abstained':bool(case['expected']) or not result.shipments}


async def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--live', action='store_true')
    parser.add_argument('--output', default='/tmp/intake-eval.json')
    args = parser.parse_args()
    corpus = json.loads((Path(__file__).resolve().parents[1]/'tests/fixtures/intake_eval.json').read_text())
    assert len({c['id'] for c in corpus['cases']}) == len(corpus['cases'])
    assert all(c['text'] and c['destination'] and isinstance(c['expected'],dict) for c in corpus['cases'])
    if not args.live:
        print(f"Validated {len(corpus['cases'])} synthetic cases. No provider called. Use --live only when a candidate model and key are configured.")
        return
    if not provider_config(public=True)['configured']:
        raise SystemExit('Configure TOC_AI_PROVIDER, TOC_AI_MODEL and its API key before live evaluation.')
    reports=[]
    for case in corpus['cases']:
        try:
            result,meta=await model_structured(Manifest,EXTRACTION_INSTRUCTIONS,{'destination':case['destination'],'pages':[{'page':1,'text':case['text']}]})
            reports.append(score(case,result)|{'provider':meta['provider'],'model':meta['model'],'metrics':meta['metrics']})
        except Exception:
            reports.append({'id':case['id'],'error':'Provider or validation failure','expected_fields':len(case['expected']),'correct_fields':0})
    expected=sum(r['expected_fields'] for r in reports)
    output={'corpus_version':corpus['version'],'cases':reports,'exact_expected_field_accuracy':sum(r['correct_fields'] for r in reports)/expected if expected else None,
            'limitations':'Starter extraction evaluation only. Does not establish matching accuracy, operational readiness, human handling-time savings, or production quality.'}
    Path(args.output).write_text(json.dumps(output,indent=2)+'\n')
    print(f'Evaluation written to {args.output}')


if __name__ == '__main__':
    asyncio.run(main())
