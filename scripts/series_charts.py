#!/usr/bin/env python3
"""Python-rendered source-series plots; only explicit qualified edges are lines."""
import html
from decimal import Decimal,InvalidOperation
from urllib.parse import urlsplit
import phase2_engine as p2
def period(a):
 y=a.get('comparison_year');m=a.get('comparison_month')
 if not isinstance(y,int) or isinstance(y,bool) or not 1000<=y<=9999:return None
 if a.get('period_kind')=='monthly_source_statistic':
  if not isinstance(m,int) or isinstance(m,bool) or not 1<=m<=12:return None
  return y*12+m-1,str(y)+'-'+str(m).zfill(2)
 if m is not None or a.get('period_kind') in ('unresolved','partial_year_source','programme_not_annual','monthly_reference_month_unresolved'):return None
 return y,str(y)
def svg(series,start_year=None,end_year=None):
 def inside(point):return (start_year is None or point['year']>=start_year) and (end_year is None or point['year']<=end_year)
 keys={p['record_key'] for p in series['source_points'] if inside(p)}
 paths=''.join(e['markup'] for e in series['segments'] if e['left'] in keys and e['right'] in keys)
 points=''.join(p['markup'] for p in series['source_points'] if p['record_key'] in keys)
 return '<svg viewBox="0 0 850 285" role="img" aria-label="原來源數列；只連接核准的相鄰期間">'+series['axes_svg']+paths+points+'</svg>'
def chart(items,allowed_edges=None,values=None):
 if not items:return None
 if len({a['comparison_group_id'] for a in items})!=1:raise ValueError('Never combine original definition groups in one chart')
 units={a['comparison_unit'] for a in items if a.get('comparison_unit') is not None}
 if len(units)!=1:return None
 positions={};omitted=[]
 for a in items:
  p=period(a)
  if p is None:omitted.append({'record_key':a['record_key'],'reason':'formal_period_unknown','raw_value':a.get('raw_value')});continue
  if p[0] in positions:return None
  positions[p[0]]=(a,p[1])
 if not positions:return None
 lo_x=min(positions);hi_x=max(positions);span_x=Decimal(hi_x-lo_x or 1);numeric={}
 for i,(a,label) in positions.items():
  raw=values.get(a['record_key']) if values is not None else a.get('comparison_value') if a.get('comparison_status')=='published_panel_limited' else None
  try:value=Decimal(str(raw)) if raw is not None else None
  except InvalidOperation:value=None
  if value is None or not value.is_finite():
   omitted.append({'record_key':a['record_key'],'year':a['comparison_year'],'month':a['comparison_month'],'reason':'unknown_or_unusable_numeric_point','raw_value':a.get('raw_value'),'value_status':a.get('value_status')});continue
  numeric[i]=(a,label,value)
 if not numeric:return None
 low=min(Decimal(0),min(v for a,l,v in numeric.values()));high=max(v for a,l,v in numeric.values());span_y=high-low or Decimal(1);points=[];xy={};segments=[]
 for i,(a,label,value) in sorted(numeric.items()):
  x=Decimal(76)+Decimal(i-lo_x)/span_x*Decimal(700);y=Decimal(220)-(value-low)/span_y*Decimal(170);xs,ys=f'{x:.2f}',f'{y:.2f}';xy[a['record_key']]=(xs,ys)
  caption=label+'：'+str(value)+' '+a['comparison_unit']+'；原值 '+str(a.get('raw_value'))+'；'+str(a.get('source_locator') or '')
  circle='<circle cx="'+xs+'" cy="'+ys+'" r="4" fill="#226758"><title>'+html.escape(caption)+'</title></circle>';url=a.get('source_url')
  if url and urlsplit(url).scheme in ('http','https'):circle='<a href="'+html.escape(url,quote=True)+'" target="_blank" rel="noopener noreferrer">'+circle+'</a>'
  points.append({'record_key':a['record_key'],'year':a['comparison_year'],'month':a['comparison_month'],'period_label':label,'reported_value':a.get('original_value'),'raw_value':a.get('raw_value'),'comparison_value':str(value),'source_id':a['source_id'],'source_sha256':a['source_sha256'],'source_url':url,'source_locator':a['source_locator'],'source_version_id':a.get('source_version_id'),'zero_interpretation':a.get('zero_interpretation'),'x':xs,'y':ys,'markup':circle})
 for (i,(a,_)),(j,(b,_)) in zip(sorted(positions.items()),sorted(positions.items())[1:]):
  pair=(a['record_key'],b['record_key'])
  if j!=i+1 or pair[0] not in xy or pair[1] not in xy:continue
  allowed=p2.compare(a,b)['status']=='published_panel_limited' and (allowed_edges is None or pair in allowed_edges)
  if not allowed:continue
  x1,y1=xy[pair[0]];x2,y2=xy[pair[1]];segments.append({'left':pair[0],'right':pair[1],'markup':'<path d="M'+x1+','+y1+' L'+x2+','+y2+'" fill="none" stroke="#226758" stroke-width="2"/>'})
 axes='<path d="M76,40V220H792" fill="none" stroke="#9dae9f"/>'
 for value in sorted({low,high}):
  y=Decimal(220)-(value-low)/span_y*Decimal(170);axes+='<text x="68" y="'+f'{y+4:.2f}'+'" text-anchor="end" font-size="11">'+html.escape(format(value,',f'))+'</text>'
 indexes=sorted(positions);ticks={indexes[round(i*(len(indexes)-1)/min(5,len(indexes)-1))] for i in range(min(5,len(indexes)-1)+1)} if len(indexes)>1 else {indexes[0]}
 for i in sorted(ticks):
  x=Decimal(76)+Decimal(i-lo_x)/span_x*Decimal(700);axes+='<text x="'+f'{x:.2f}'+'" y="246" text-anchor="middle" font-size="11">'+html.escape(positions[i][1])+'</text>'
 a=items[0];fac=a['facets'];years=sorted({p['year'] for p in points});qualifiers=' '.join(str(fac.get(k) or '') for k in ('entity','facility_or_reader_category'));label=qualifiers+'｜'+a['raw_indicator']+'（'+a['comparison_unit']+'）｜'+str(years[0])+'–'+str(years[-1])+'｜'+a['source_id']
 result={'comparison_group_id':a['comparison_group_id'],'label':label,'entity':fac.get('entity'),'facility':fac.get('facility_or_reader_category'),'indicator':a['raw_indicator'],'unit':a['comparison_unit'],'source_id':a['source_id'],'source_edition_raw':a.get('source_edition_raw'),'years':years,'source_points':points,'omitted_points':omitted,'segments':segments,'axes_svg':axes,'plotted_points':len(points),'drawable_segments':len(segments),'original_positions':len(items),'gap_policy':'Only original numeric points. Unknown/missing/duplicate periods and unapproved boundaries never create a connecting line.','method_invariance_certified':False}
 result['svg']=svg(result);return result
