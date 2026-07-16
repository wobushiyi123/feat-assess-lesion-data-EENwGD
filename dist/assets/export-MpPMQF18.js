import{c9 as v,ca as k,cb as m}from"./vendor-DJlWTEru.js";import{g as S}from"./recist-NvwWc3n_.js";function l(e){if(!e)return"-";const t=S(e),n={完全缓解:"CR",部分缓解:"PR",疾病稳定:"SD",疾病进展:"PD",无法评估:"NE","非完全缓解/非疾病进展":"Non-CR/Non-PD",不适用:"不适用"}[t]||e;return t===e?e:`${t}(${n})`}function $(e){return e.overall_match===!0?"一致":e.overall_match===!1?"不一致":"无人工数据"}function b(e,t){const o=e[t];return o==null?"-":o?"有":"无"}function x(e){return{受试者编号:e.subject_id||"-",时间点:e.timepoint||(e.cycle_number?`周期${e.cycle_number}`:"-"),"靶病灶评估(程序)":l(e.target_status),"靶病灶评估(人工)":e.manual_target_status?l(e.manual_target_status):"-","非靶病灶评估(程序)":l(e.non_target_status),"非靶病灶评估(人工)":e.manual_non_target_status?l(e.manual_non_target_status):"-","新病灶(程序)":b(e,"has_new_lesion"),"新病灶(人工)":e.has_manual_data!==!1?b(e,"manual_has_new_lesion"):"-","总体疗效评估(程序)":l(e.overall_status),"总体疗效评估(人工)":e.manual_overall_status?l(e.manual_overall_status):"-",是否一致:$(e),程序判定理由:e.overall_reason||"-"}}function h(e){const t=[];return e.forEach(o=>{(o.timepoints||[]).forEach(n=>{t.push(x({...n,subject_id:o.subject_id,subject_name:o.subject_name}))})}),t}function z(e){return Object.keys(e[0]||{}).map(o=>{let n=o.length*2;return e.forEach(a=>{const i=[...String(a[o]||"")].reduce((s,c)=>s+(c.charCodeAt(0)>127?2:1),0);i>n&&(n=i)}),{wch:Math.min(Math.max(n+2,10),60)}})}function P(e,t){const o=m.json_to_sheet(e);o["!cols"]=z(e);const n=m.book_new();return m.book_append_sheet(n,o,t),n}async function w(e,t,o="数据"){if(!e||e.length===0)return alert("没有可导出的数据"),"empty";const n=P(e,o);if(typeof window<"u"&&window.showSaveFilePicker)try{const a=await window.showSaveFilePicker({suggestedName:t,types:[{description:"Excel 工作簿",accept:{"application/vnd.openxmlformats-officedocument.spreadsheetml.sheet":[".xlsx"]}}]}),r=v(n,{bookType:"xlsx",type:"array"}),i=await a.createWritable();return await i.write(r),await i.close(),"picker"}catch(a){if(a&&a.name==="AbortError")return"cancelled";console.warn("showSaveFilePicker failed, fallback to download",a)}return k(n,t),"download"}async function T(e,t="评估数据.xlsx",o="评估数据"){return w(e.map(x),t,o)}async function R(e,t="受试者概览.xlsx"){return w(h(e),t,"受试者概览")}function y(e,t,o=""){if(!t||t.length===0){alert("没有可导出的数据");return}const n=Object.keys(t[0]),a=new Date,r=d=>String(d).padStart(2,"0"),i=`${a.getFullYear()}-${r(a.getMonth()+1)}-${r(a.getDate())} ${r(a.getHours())}:${r(a.getMinutes())}`,s=n.map(d=>`<th>${d}</th>`).join(""),c=t.map(d=>`<tr>${n.map(g=>{const _=d[g]||"";return`<td${g.includes("理由")?' class="reason-col"':""}>${u(_)}</td>`}).join("")}</tr>`).join(""),p=`<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<title>${e}</title>
<style>
  @page { size: landscape; margin: 12mm; }
  * { box-sizing: border-box; }
  body { font-family: "Microsoft YaHei", "SimSun", sans-serif; margin: 0; padding: 24px; color: #303133; }
  .report-title { font-size: 22px; font-weight: 700; text-align: center; margin-bottom: 6px; }
  .report-subtitle { font-size: 14px; color: #606266; text-align: center; margin-bottom: 4px; }
  .report-meta { font-size: 12px; color: #909399; text-align: center; margin-bottom: 20px; }
  .stats-row { display: flex; gap: 24px; justify-content: center; margin-bottom: 16px; }
  .stat-item { font-size: 13px; color: #606266; }
  .stat-item strong { color: #409eff; font-size: 16px; margin-right: 4px; }
  table { width: 100%; border-collapse: collapse; font-size: 11px; }
  th { background: #409eff; color: #fff; padding: 7px 5px; text-align: center; border: 1px solid #d0d0d0; white-space: nowrap; }
  td { padding: 5px 4px; border: 1px solid #e0e0e0; text-align: center; }
  tr:nth-child(even) { background: #f7f9fc; }
  .reason-col { text-align: left; max-width: 320px; word-break: break-word; white-space: normal; }
  .footer { margin-top: 16px; font-size: 11px; color: #c0c4cc; text-align: center; }
  @media print { body { padding: 0; } .no-print { display: none; } }
</style>
</head>
<body>
  <div class="report-title">${e}</div>
  ${o?`<div class="report-subtitle">${o}</div>`:""}
  <div class="report-meta">导出时间：${i}　|　共 ${t.length} 条记录</div>
  <table>
    <thead><tr>${s}</tr></thead>
    <tbody>${c}</tbody>
  </table>
  <div class="footer">本报告由 RECIST 病灶评估系统自动生成</div>
  <script>
    window.onload = function() {
      setTimeout(function() { window.print(); }, 300);
    };
    window.onafterprint = function() { window.close(); };
  <\/script>
</body>
</html>`,f=window.open("","_blank");if(!f){alert("请允许弹出窗口以导出PDF");return}f.document.write(p),f.document.close()}function D(e,t,o=""){const n=t.map(x);y(e,n,o)}function F(e,t="受试者概览"){const o=h(e);y(t,o,"")}function u(e){return String(e).replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;").replace(/"/g,"&quot;")}async function L(e,t){const o=new Date().toLocaleString("zh-CN"),n=`<html xmlns:o='urn:schemas-microsoft-com:office:office' xmlns:w='urn:schemas-microsoft-com:office:word' xmlns='http://www.w3.org/1999/xhtml'>
<head>
<meta charset='utf-8'>
<title>${u(e)}</title>
<style>
  body { font-family: "Microsoft YaHei", "SimSun", sans-serif; color: #1f2937; font-size: 13px; line-height: 1.7; margin: 0; padding: 0 24px; }
  h2 { font-size: 17px; font-weight: 700; color: #1e6bd6; margin: 22px 0 10px; padding-bottom: 6px; border-bottom: 2px solid #1e6bd6; }
  h3 { font-size: 14px; font-weight: 600; color: #1f2937; margin: 16px 0 8px; }
  h4 { font-size: 13px; font-weight: 600; color: #374151; margin: 12px 0 6px; }
  p { margin: 8px 0; }
  ul, ol { padding-left: 22px; margin: 8px 0; }
  li { margin: 4px 0; }
  code { background: #f3f4f6; padding: 1px 5px; border-radius: 3px; font-family: Consolas, "Courier New", monospace; font-size: 12px; color: #d63384; }
  table { border-collapse: collapse; width: 100%; margin: 10px 0; font-size: 12px; }
  th { background: #1e6bd6; color: #fff; padding: 7px 8px; border: 1px solid #cfd8e3; text-align: left; }
  td { padding: 6px 8px; border: 1px solid #e5e7eb; vertical-align: top; }
  .formula-box { background: #0f172a; color: #e2e8f0; padding: 12px 16px; border-radius: 6px; margin: 10px 0; font-family: Consolas, "Courier New", monospace; font-size: 12px; line-height: 1.9; }
  .formula-box code { color: #e2e8f0; background: transparent; padding: 0; }
  .help-callout { background: #e8f0fe; border-left: 4px solid #1e6bd6; padding: 10px 14px; border-radius: 4px; margin: 10px 0; }
</style>
</head>
<body>
  <div style="text-align:center; margin: 16px 0 20px;">
    <h1 style="color:#1e6bd6; font-size:22px; font-weight:700; margin:0;">${u(e)}</h1>
    <p style="color:#909399; font-size:12px; margin:4px 0 0;">RECIST 病灶评估系统 · 使用帮助　|　导出时间：${o}</p>
  </div>
  ${t}
  <div style="margin-top:20px; font-size:11px; color:#c0c4cc; text-align:center; border-top:1px solid #e5e7eb; padding-top:10px;">本文档由 RECIST 病灶评估系统自动生成</div>
</body>
</html>`,a=new Blob(["\uFEFF"+n],{type:"application/msword"}),r=`${e.replace(/[\\/:*?"<>|]/g,"_")}.doc`;if(typeof window<"u"&&window.showSaveFilePicker)try{const p=await(await window.showSaveFilePicker({suggestedName:r,types:[{description:"Word 文档",accept:{"application/msword":[".doc"]}}]})).createWritable();return await p.write(a),await p.close(),"picker"}catch(c){if(c&&c.name==="AbortError")return"cancelled";console.warn("showSaveFilePicker failed, fallback to download",c)}const i=URL.createObjectURL(a),s=document.createElement("a");return s.href=i,s.download=r,document.body.appendChild(s),s.click(),document.body.removeChild(s),setTimeout(()=>URL.revokeObjectURL(i),1e3),"download"}export{R as a,T as b,F as c,D as d,w as e,L as f};
