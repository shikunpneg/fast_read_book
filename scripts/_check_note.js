const fs = require('fs');
const h = fs.readFileSync('e:/nlp/ltp/kg_book_interactive_v6.html', 'utf-8');
const js = fs.readFileSync('e:/nlp/ltp/kg_app_v6.js', 'utf-8');
const css = fs.readFileSync('e:/nlp/ltp/kg_style_v6.css', 'utf-8');
console.log('dp-note in HTML:', h.includes('dp-note'));
console.log('dp-note in JS:', js.includes('dp-note'));
console.log('dp-note in CSS:', css.includes('dp-note'));
console.log('v=3 in HTML:', h.includes('v=3'));