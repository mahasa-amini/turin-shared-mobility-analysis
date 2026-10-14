from pathlib import Path
import re
r=Path('/Users/mahasaamini/Documents/transport_exercise'); errors=[]; count=0
for p in [r/'README.md',*sorted((r/'docs').rglob('*.md'))]:
 for link in re.findall(r'!?\[[^\]]*\]\(([^)]+)\)',p.read_text()):
  link=link.split('#')[0]
  if not link or '://' in link or link.startswith('mailto:'): continue
  count+=1
  if not (p.parent/link).exists(): errors.append((str(p.relative_to(r)),link))
print({'local_links_checked':count,'missing':errors}); assert not errors
