#!/usr/bin/env python3
"""Сводит прогоны корпуса code-review-security-audit в одну таблицу.

    python3 fixtures/security-audit/summarize.py a.json b.json ...

Каждый файл — результат `run-cases.mjs`. Таблица: по кейсу — что ожидалось,
найдено ли, сколько ложных срабатываний и сколько прочих находок. Плюс
сводка: сколько прогонов нашли ожидаемую слабость, сколько — нет, сколько
ложных срабатываний, сколько это стоило.

Три корзины, и они разные по природе:

* **найдено** — находка в ожидаемой области, класс из списка ожидаемых. Это
  recall.
* **ложное срабатывание** — находка в области near-miss: место, где код
  заведомо безопасен. Это precision, и оно проверяемо.
* **прочее** — всё остальное: мнения пайплайна об окружающем коде. Корпус
  их не разбирает и не называет правдой или ложью.

Почему область, а не точная строка. Пайплайн называет номер строки, на
которой, по его мнению, находка, и этот номер иногда не совпадает с
настоящим: строка за пределами диффа достраивается, а строка функции
иногда называется вместо строки внутри неё. Поэтому находка приписывается к
ближайшей области кейса, а не сравнивается с диапазоном строк наравне.

Печатает число прочитанных файлов: молчаливый сканер хуже, чем сканер,
который ничего не нашёл.
"""
import json
import re
import sys
from collections import Counter

CWE = re.compile(r'cwe[-_ ]?(\d+)', re.IGNORECASE)


def norm_cwe(value):
    """`CWE-89`, `cwe 89`, `89` → `CWE-89`. Nothing → ''."""
    if value is None:
        return ''
    m = CWE.search(str(value))
    return f'CWE-{m.group(1)}' if m else ''


def distance(line, ranges):
    """Насколько строка далеко от области. 0 — внутри области."""
    if not ranges or line is None:
        return 0
    return min(min(abs(line - lo), abs(line - hi)) for lo, hi in ranges)


def assign(finding, expect, rules):
    """К какой области кейса относится находка: 'expect', 'rule' или None."""
    file = finding.get('file')
    line = finding.get('line') if isinstance(finding.get('line'), int) else None
    candidates = []
    if expect.get('file') == file:
        candidates.append(('expect', expect.get('lines') or [], expect.get('cwe', [])))
    for rule in rules:
        if rule.get('file') == file:
            candidates.append(('rule', rule.get('lines') or [], rule.get('cwe', [])))
    if not candidates:
        return None
    best = None
    for kind, ranges, cwe in candidates:
        d = distance(line, ranges)
        if best is None or d < best[1]:
            best = (kind, d, cwe)
    return best


def load_expected():
    here = __file__.replace('summarize.py', 'cases/expected.json')
    with open(here, encoding='utf-8') as f:
        return json.load(f)['cases']


def load(path):
    with open(path, encoding='utf-8') as f:
        return json.load(f)


def label(arm):
    bits = [arm.get('spec_version', '?')]
    if arm.get('repeats'):
        bits.append(f"{arm['repeats']}x")
    return ' · '.join(bits)


def classify(findings, case):
    """(найдено, ложные срабатывания, прочее, классы ожидаемой находки)."""
    expect = case.get('expect') or {}
    rules = case.get('must_not_report', []) or []
    want = {norm_cwe(c) for c in expect.get('cwe', [])}

    found = False
    false_positives = []
    additional = []
    classes = Counter()

    for f in findings:
        cwe = norm_cwe(f.get('cwe'))
        where = assign(f, expect, rules)
        if where is None:
            additional.append(f)
            continue
        kind, _d, cwe_list = where
        allowed = {norm_cwe(c) for c in cwe_list}
        if kind == 'expect':
            if cwe in want:
                found = True
                classes[cwe] += 1
                continue
            additional.append(f)
            continue
        if cwe in allowed:
            false_positives.append(f)
            continue
        additional.append(f)

    return found, false_positives, additional, classes


def main():
    paths = sys.argv[1:]
    if not paths:
        print('nothing to read')
        return 1
    arms = [load(p) for p in paths]
    expected = load_expected()
    print(f'прочитано файлов: {len(arms)}')

    per_case = {}
    for arm in arms:
        for case in arm['cases']:
            per_case.setdefault(case['id'], {})[label(arm)] = case

    names = [label(a) for a in arms]
    header = f"{'кейс':22} {'найдено':9} {'ложных':8} {'прочих':8} " + ' | '.join(names)
    print('\n' + header)
    totals = {'runs': 0, 'found': 0, 'errors': 0, 'fp': 0, 'additional': 0}

    for cid in sorted(per_case):
        exp = expected.get(cid, {})
        expect = exp.get('expect') or {}
        cells = []
        found_here = runs_here = fp_here = add_here = 0
        classes = Counter()
        for name in names:
            case = per_case[cid].get(name)
            if not case:
                cells.append('—')
                continue
            marks = []
            for run in case['runs']:
                if 'error' in run:
                    marks.append('ошибка')
                    totals['errors'] += 1
                    continue
                runs_here += 1
                found, fps, extra, cls = classify(run.get('findings', []), exp)
                totals['runs'] += 1
                totals['found'] += 1 if found else 0
                totals['fp'] += len(fps)
                totals['additional'] += len(extra)
                if found:
                    found_here += 1
                fp_here += len(fps)
                add_here += len(extra)
                classes.update(cls)
                marks.append('да' if found else 'нет')
            cells.append(' '.join(marks) or '—')
        print(f'{cid:22} {found_here:>4}/{runs_here:<4} {fp_here:>8} {add_here:>8} ' + ' | '.join(cells))
        if classes:
            print(f"{'':22} названа классами: " + ', '.join(f'{c}×{n}' for c, n in classes.most_common()))

    print()
    for arm in arms:
        cost = sum(r.get('cost_usdc', 0) for c in arm['cases'] for r in c['runs'])
        runs_n = sum(len(c['runs']) for c in arm['cases'])
        errors = sum(1 for c in arm['cases'] for r in c['runs'] if 'error' in r)
        print(f"{label(arm):28} прогонов {runs_n:2}  ошибок {errors}  $ {cost:.5f}")
    print()
    print(f"найдено ожидаемое: {totals['found']}/{totals['runs']} прогонов")
    print(f"ложных срабатываний: {totals['fp']}")
    print(f"прочих находок: {totals['additional']}")
    return 0


if __name__ == '__main__':
    sys.exit(main())
