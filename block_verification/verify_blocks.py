import sys, os, re, difflib
import pandas as pd
RAW = sys.argv[1]; CSV = sys.argv[2]; OUT = sys.argv[3]
files = {f.replace(' ', ''): f for f in os.listdir(RAW) if re.match(r'^(A_B|B_A)_', f)}
SEGTXT = {'AC': 'down str. to sorting', 'CB': 'sorting to up', 'BC': 'up str. to sorting', 'CA': 'sorting to down'}
def raw_times(fname, seg2):
    d = pd.read_excel(os.path.join(RAW, fname), header=None)
    times, labels = [], []
    for c in range(d.shape[1] - 1):
        for r in range(d.shape[0]):
            cell = d.iat[r, c]
            if isinstance(cell, str) and 'timestamp' in cell.lower() and SEGTXT[seg2] in cell.lower():
                v = d.iat[r, c + 1]
                if pd.notna(v):
                    times.append(int(v)); labels.append(cell.split(' Timestamp')[0].strip())
    return times, labels
# (segment, direction prefix, raw column, label rule: which letter gives this segment's fault)
plan = {'forward_AC': ('A_B', 'AC', 0), 'forward_CB': ('A_B', 'CB', 1),
        'backward_BC': ('B_A', 'BC', 1), 'backward_CA': ('B_A', 'CA', 0)}
summary = []
for seg, (dirn, col, letter) in plan.items():
    seq = []
    for p in ['3.5', '4', '5', '6']:
        for cond in ['N_N', 'N_Y', 'Y_N', 'Y_Y']:
            fname = files[f'{dirn}_{p}_{cond}.xlsx']
            times, labels = raw_times(fname, col)
            fault = 1 if cond.split('_')[letter] == 'Y' else 0
            for k, t in enumerate(times):
                seq.append(dict(block_id=f'{dirn}_{p}_{cond}', pressure=float(p), fault=fault, time=t, raw_row=k, label_in_raw=labels[k]))
    raw = pd.DataFrame(seq)
    csv = pd.read_csv(os.path.join(CSV, seg + '.csv'))
    a = list(zip(csv.Pressure.astype(float), csv.Time.astype(int), csv.Mechanism.astype(int)))
    b = list(zip(raw.pressure, raw.time, raw.fault))
    sm = difflib.SequenceMatcher(None, a, b, autojunk=False)
    block = [None] * len(a); ops = []
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag == 'equal':
            for k in range(i2 - i1): block[i1 + k] = raw.block_id[j1 + k]
        else:
            ops.append((tag, i1, i2, j1, j2, a[i1:i2], b[j1:j2]))
    matched = sum(x is not None for x in block)
    # unmatched CSV rows: assign block of neighbours only if the same condition on both sides and same pressure/label
    unresolved = [i for i, x in enumerate(block) if x is None]
    for i in unresolved:
        prev = next((block[j] for j in range(i - 1, -1, -1) if block[j]), None)
        nxt = next((block[j] for j in range(i + 1, len(block)) if block[j]), None)
        if prev and prev == nxt:
            block[i] = prev + '*'
    out = csv.copy(); out['block_id'] = block; out['row_in_csv'] = range(len(out))
    out.to_csv(os.path.join(OUT, seg + '_with_blocks.csv'), index=False)
    print(f'== {seg}: CSV rows {len(a)}, raw rows {len(b)}, matched exactly {matched}, non-equal opcodes {len(ops)}')
    for o in ops: print('   ', o[0], 'csv', (o[1], o[2]), o[5][:4], '| raw', (o[3], o[4]), o[6][:4])
    print('    still unassigned:', sum(x is None for x in block), '| assigned by neighbours (*):', sum(1 for x in block if x and x.endswith('*')))
    print('    blocks in CSV:', out.block_id.str.rstrip('*').nunique(), '| rows per block:', out.block_id.str.rstrip('*').value_counts().sort_index().to_dict())
