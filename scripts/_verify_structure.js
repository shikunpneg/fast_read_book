const fs = require('fs');
const base = 'e:/nlp/ltp';

const html = fs.readFileSync(`${base}/kg_book_interactive_v6.html`, 'utf-8');
const checks = {
    '#network div': html.includes('id="network"'),
    '#detail-panel div': html.includes('id="detail-panel"'),
    'CSS reference': html.includes('kg_style_v6.css'),
    'JS reference': html.includes('kg_app_v6.js'),
    'CSS file': fs.existsSync(`${base}/kg_style_v6.css`),
    'JS file': fs.existsSync(`${base}/kg_app_v6.js`),
    'JSON data file': fs.existsSync(`${base}/kg_entity_v6.json`),
    'build_v6.py': fs.existsSync(`${base}/build_v6.py`),
};

let allOk = true;
for (const [k, v] of Object.entries(checks)) {
    console.log(`${v ? '  OK' : '  FAIL'}  ${k}`);
    if (!v) allOk = false;
}
console.log(allOk ? '\nAll checks passed!' : '\nSome checks FAILED!');