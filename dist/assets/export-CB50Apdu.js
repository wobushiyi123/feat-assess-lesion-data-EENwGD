import{c9 as b,ca as w,cb as d}from"./vendor-DJlWTEru.js";import{g as $}from"./recist-NvwWc3n_.js";function l(e){if(!e)return"-";const t=$(e),o={完全缓解:"CR",部分缓解:"PR",疾病稳定:"SD",疾病进展:"PD",无法评估:"NE","非完全缓解/非疾病进展":"Non-CR/Non-PD",不适用:"不适用"}[t]||e;return t===e?e:`${t}(${o})`}function z(e){return e.overall_match===!0?"一致":e.overall_match===!1?"不一致":"无人工数据"}function h(e,t){const n=e[t];return n==null?"-":n?"有":"无"}function x(e){return{受试者编号:e.subject_id||"-",时间点:e.timepoint||(e.cycle_number?`周期${e.cycle_number}`:"-"),"靶病灶评估(程序)":l(e.target_status),"靶病灶评估(人工)":e.manual_target_status?l(e.manual_target_status):"-","非靶病灶评估(程序)":l(e.non_target_status),"非靶病灶评估(人工)":e.manual_non_target_status?l(e.manual_non_target_status):"-","新病灶(程序)":h(e,"has_new_lesion"),"新病灶(人工)":e.has_manual_data!==!1?h(e,"manual_has_new_lesion"):"-","总体疗效评估(程序)":l(e.overall_status),"总体疗效评估(人工)":e.manual_overall_status?l(e.manual_overall_status):"-",是否一致:z(e),程序判定理由:e.overall_reason||"-"}}function y(e){const t=[];return e.forEach(n=>{(n.timepoints||[]).forEach(o=>{t.push(x({...o,subject_id:n.subject_id,subject_name:n.subject_name}))})}),t}function _(e){return Object.keys(e[0]||{}).map(n=>{let o=n.length*2;return e.forEach(a=>{const i=[...String(a[n]||"")].reduce((c,s)=>c+(s.charCodeAt(0)>127?2:1),0);i>o&&(o=i)}),{wch:Math.min(Math.max(o+2,10),60)}})}function P(e,t){const n=d.json_to_sheet(e);n["!cols"]=_(e);const o=d.book_new();return d.book_append_sheet(o,n,t),o}async function k(e,t,n="数据"){if(!e||e.length===0)return alert("没有可导出的数据"),"empty";const o=P(e,n);if(typeof window<"u"&&window.showSaveFilePicker)try{const a=await window.showSaveFilePicker({suggestedName:t,types:[{description:"Excel 工作簿",accept:{"application/vnd.openxmlformats-officedocument.spreadsheetml.sheet":[".xlsx"]}}]}),r=b(o,{bookType:"xlsx",type:"array"}),i=await a.createWritable();return await i.write(r),await i.close(),"picker"}catch(a){if(a&&a.name==="AbortError")return"cancelled";console.warn("showSaveFilePicker failed, fallback to download",a)}return w(o,t),"download"}async function T(e,t){if(!e||!e.length||!e.some(o=>o.data&&o.data.length))return alert("没有可导出的数据"),"empty";const n=d.book_new();if(e.forEach(o=>{const a=d.json_to_sheet(o.data||[]);a["!cols"]=_(o.data||[]),d.book_append_sheet(n,a,(o.name||"Sheet").slice(0,31))}),typeof window<"u"&&window.showSaveFilePicker)try{const o=await window.showSaveFilePicker({suggestedName:t,types:[{description:"Excel 工作簿",accept:{"application/vnd.openxmlformats-officedocument.spreadsheetml.sheet":[".xlsx"]}}]}),a=b(n,{bookType:"xlsx",type:"array"}),r=await o.createWritable();return await r.write(a),await r.close(),"picker"}catch(o){if(o&&o.name==="AbortError")return"cancelled";console.warn("showSaveFilePicker failed, fallback to download",o)}return w(n,t),"download"}async function F(e,t="评估数据.xlsx",n="评估数据"){return k(e.map(x),t,n)}async function R(e,t="受试者概览.xlsx"){return k(y(e),t,"受试者概览")}function v(e,t,n=""){if(!t||t.length===0){alert("没有可导出的数据");return}const o=Object.keys(t[0]),a=new Date,r=p=>String(p).padStart(2,"0"),i=`${a.getFullYear()}-${r(a.getMonth()+1)}-${r(a.getDate())} ${r(a.getHours())}:${r(a.getMinutes())}`,c=o.map(p=>`<th>${p}</th>`).join(""),s=t.map(p=>`<tr>${o.map(g=>{const S=p[g]||"";return`<td${g.includes("理由")?' class="reason-col"':""}>${u(S)}</td>`}).join("")}</tr>`).join(""),f=`<!DOCTYPE html>
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
  ${n?`<div class="report-subtitle">${n}</div>`:""}
  <div class="report-meta">导出时间：${i}　|　共 ${t.length} 条记录</div>
  <table>
    <thead><tr>${c}</tr></thead>
    <tbody>${s}</tbody>
  </table>
  <div class="footer">本报告由 RECIST 病灶评估系统自动生成</div>
  <script>
    window.onload = function() {
      setTimeout(function() { window.print(); }, 300);
    };
    window.onafterprint = function() { window.close(); };
  <\/script>
</body>
</html>`,m=window.open("","_blank");if(!m){alert("请允许弹出窗口以导出PDF");return}m.document.write(f),m.document.close()}function D(e,t,n=""){const o=t.map(x);v(e,o,n)}function N(e,t="受试者概览"){const n=y(e);v(t,n,"")}function u(e){return String(e).replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;").replace(/"/g,"&quot;")}async function L(e,t){const n=new Date().toLocaleString("zh-CN"),o=`<html xmlns:o='urn:schemas-microsoft-com:office:office' xmlns:w='urn:schemas-microsoft-com:office:word' xmlns='http://www.w3.org/1999/xhtml'>
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
    <p style="color:#909399; font-size:12px; margin:4px 0 0;">RECIST 病灶评估系统 · 使用帮助　|　导出时间：${n}</p>
  </div>
  ${t}
  <div style="margin-top:20px; font-size:11px; color:#c0c4cc; text-align:center; border-top:1px solid #e5e7eb; padding-top:10px;">本文档由 RECIST 病灶评估系统自动生成</div>
</body>
</html>`,a=new Blob(["\uFEFF"+o],{type:"application/msword"}),r=`${e.replace(/[\\/:*?"<>|]/g,"_")}.doc`;if(typeof window<"u"&&window.showSaveFilePicker)try{const f=await(await window.showSaveFilePicker({suggestedName:r,types:[{description:"Word 文档",accept:{"application/msword":[".doc"]}}]})).createWritable();return await f.write(a),await f.close(),"picker"}catch(s){if(s&&s.name==="AbortError")return"cancelled";console.warn("showSaveFilePicker failed, fallback to download",s)}const i=URL.createObjectURL(a),c=document.createElement("a");return c.href=i,c.download=r,document.body.appendChild(c),c.click(),document.body.removeChild(c),setTimeout(()=>URL.revokeObjectURL(i),1e3),"download"}export{k as a,R as b,F as c,N as d,T as e,D as f,L as g};
