import math
def w(k,n,z=1.96):
    p=k/n; d=1+z*z/n; c=(p+z*z/(2*n))/d; h=z*math.sqrt(p*(1-p)/n+z*z/(4*n*n))/d; return (round(c-h,3),round(c+h,3))
rows=[('BM25 ID R@1',1.0),('BM25 PARA R@1',0.067),('BM25 PARA R@10',0.42),('bge+pfx ID R@1',0.133),('bge+pfx ID R@10',0.293),('bge+pfx PARA R@1',0.887),('bge+pfx PARA R@10',1.0),('bge nopfx PARA R@1',0.853),('bge nopfx ID R@1',0.087),('Qwen+inst ID R@1',0.24),('Qwen+inst ID R@10',0.493),('Qwen+inst PARA R@1',0.80),('Qwen+inst PARA R@10',0.987)]
for name,p in rows:
    k=round(p*150); print(name,k,'/150',w(k,150))
