#!/usr/bin/env python3
"""Render all bundled prose to offline HTML and keep local document links local."""
import argparse,html,re
from pathlib import Path
from markdown_it import MarkdownIt

def main():
 parser=argparse.ArgumentParser();parser.add_argument('--base',type=Path,required=True);base=parser.parse_args().base.resolve();md=MarkdownIt('commonmark',{'html':False}).enable('table')
 def heading(tokens,index,options,env):
  text=tokens[index+1].content;slug=re.sub(r'[^\w\s-]','',text.lower());slug=re.sub(r'\s+','-',slug.strip());return '<'+tokens[index].tag+' id="'+html.escape(slug,quote=True)+'">'
 md.renderer.rules['heading_open']=heading
 for source in base.rglob('*.md'):
  if source.parent==base/'04-assembly'and source.name in ['soldering.md','soldering.zh-CN.md']:continue
  text=source.read_text();title=next((x.lstrip('# ').strip()for x in text.splitlines()if x.startswith('# ')),source.stem);zh='.zh-CN'in source.name
  import os
  back=Path(os.path.relpath(base/('index.zh-CN.html'if zh else'index.html'),source.parent)).as_posix();page=f'''<!doctype html><html lang="{'zh-CN'if zh else'en'}"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{html.escape(title)}</title><style>body{{margin:0;background:#eeede6;color:#203128;font:17px/1.75 Georgia,"Noto Serif CJK SC",serif}}main{{max-width:1100px;padding:36px 24px;margin:auto}}header{{border-top:7px solid #203128;padding:16px 0}}h1{{font-size:clamp(30px,4vw,50px);line-height:1.2}}h2{{border-top:1px solid #b9c2b5;padding-top:28px;margin-top:38px}}a{{color:inherit;text-underline-offset:4px}}img{{max-width:100%}}pre{{overflow:auto;background:#dfe3d9;padding:20px}}code{{font-size:14px}}table{{display:block;overflow-x:auto;border-collapse:collapse;font-size:14px}}td,th{{text-align:left;vertical-align:top;padding:10px;border-bottom:1px solid #c2c9bc;min-width:70px}}blockquote{{border-left:4px solid #af4c29;padding-left:18px}}@media(max-width:600px){{main{{padding:22px 15px}}body{{font-size:16px}}}}@media print{{body{{background:white}}table{{display:table;font-size:10px}}pre{{white-space:pre-wrap}}}}</style><main><header><a href="{back}">{'返回交付目录'if zh else'Back to delivery index'}</a></header>{md.render(text)}</main></html>''';source.with_suffix('.html').write_text(page)
 for path in base.rglob('*.html'):
  def link(match):
   key,url=match.groups();url=html.unescape(url)
   if re.match(r'^[a-z]+:|^#',url):return match.group(0)
   raw,sep,anchor=url.partition('#');p=path.parent/raw
   if p.suffix=='.md'and p.with_suffix('.html').is_file():url=str(Path(raw).with_suffix('.html'))+('#'+anchor if sep else'')
   return key+'="'+html.escape(url,quote=True)+'"'
  path.write_text(re.sub(r'(href|src)="([^"]+)"',link,path.read_text()))
 print('Offline HTML prose generated; local document links resolved')
if __name__=='__main__':main()
