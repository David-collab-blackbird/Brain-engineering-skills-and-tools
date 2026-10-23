import json, sys
p = sys.argv[1]
d = json.load(open(p))
def f(x, k='mean', nd=3):
    if x is None:
        return 'inf'
    v = x.get(k)
    return f"{v:.{nd}f}" if isinstance(v, float) else str(v)
print('| class | sets (s1) | tasks unreachable@400 query / nbhd | split-conf K̂ query (cov) | split-conf K̂ nbhd (cov, ~tokens) | CRC-recall K (mean recall / all-items) | adaptive gap set: cov, mean size, p90 | cross-seed nbhd cov s2 / s3 |')
print('|---|---|---|---|---|---|---|---|')
for c, s in d.items():
    qK = 'inf' if s.get('query_K') is None else f"{s['query_K']['mean']:.0f} [{s['query_K']['p05']:.0f}–{s['query_K']['p95']:.0f}]"
    qc = f(s.get('query_cov'))
    nK = 'inf' if s.get('nbhd_K') is None else f"{s['nbhd_K']['mean']:.0f} [{s['nbhd_K']['p05']:.0f}–{s['nbhd_K']['p95']:.0f}] (n={s['nbhd_K']['n']}/200 finite)"
    nc = f(s.get('nbhd_cov'))
    nt = f(s.get('nbhd_tok'), nd=0)
    if s.get('crc_K') is None:
        crc = 'inf'
    else:
        crc = f"{s['crc_K']['mean']:.0f} ({f(s['crc_meanrecall'])} / {f(s['crc_allitems'])})"
    ad = f"{f(s.get('adapt_cov'))}, {f(s.get('adapt_size_mean'), nd=0)}, {f(s.get('adapt_size_p90'), nd=0)}"
    xs = f"{s.get('xseed_nbhd_cov_s2','-')} / {s.get('xseed_nbhd_cov_s3','-')} (K̂={s.get('xseed_nbhd_K','-')})"
    print(f"| {c} | {s['n_sets_total']} | {s['inf_rate_query']:.2f} / {s['inf_rate_nbhd']:.2f} | {qK} ({qc}) | {nK} ({nc}, {nt}) | {crc} | {ad} | {xs} |")
