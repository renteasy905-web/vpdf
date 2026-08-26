from flask import Flask, request, jsonify, send_file, render_template_string
from flask_cors import CORS
from pypdf import PdfReader, PdfWriter
import fitz
import pytesseract
from PIL import Image
from io import BytesIO
import os
import re
import json
import tempfile
import zipfile

app = Flask(__name__)
CORS(app)
app.config['MAX_CONTENT_LENGTH'] = 100 * 1024 * 1024

ALLOWED_EXTENSIONS = {'pdf'}
RANGE_RE = r'(\d{1,4})\s*(?:-|–|—|to)\s*(\d{1,4})'


def allowed_file(filename):
    return bool(filename) and '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def normalize_text(text):
    if not text:
        return ''
    text = text.replace('\u00a0', ' ')
    text = text.replace('‐', '-').replace('‑', '-').replace('−', '-')
    text = re.sub(r'[ \t]+', ' ', text)
    return text.strip()


def parse_chapter_declarations(text):
    """Find declarations such as 1-4 Chapter 1 or Chapter 1: 1-4.
    The numbers are PDF page numbers, NOT question numbers.
    """
    text = normalize_text(text)
    if not text:
        return []
    text = re.sub(r'\s+', ' ', text)
    results = []

    p1 = re.compile(rf'(?i)({RANGE_RE}).{{0,100}}?\bchapter\s*([0-9]+)\b')
    for m in p1.finditer(text):
        r = re.search(RANGE_RE, m.group(1))
        if r:
            results.append({'chapter': int(m.group(2)), 'start': int(r.group(1)), 'end': int(r.group(2)), 'source': m.group(0).strip()})

    p2 = re.compile(rf'(?i)\bchapter\s*([0-9]+)\b.{{0,100}}?({RANGE_RE})')
    for m in p2.finditer(text):
        r = re.search(RANGE_RE, m.group(2))
        if r:
            results.append({'chapter': int(m.group(1)), 'start': int(r.group(1)), 'end': int(r.group(2)), 'source': m.group(0).strip()})

    unique = {}
    for item in results:
        if item['start'] >= 1 and item['end'] >= item['start']:
            unique[(item['chapter'], item['start'], item['end'])] = item
    return list(unique.values())


def usable_text(text):
    return len(re.sub(r'\s+', '', text or '')) >= 20


def ocr_page(page):
    matrix = fitz.Matrix(180 / 72, 180 / 72)
    pix = page.get_pixmap(matrix=matrix, alpha=False)
    image = Image.frombytes('RGB', (pix.width, pix.height), pix.samples)
    return normalize_text(pytesseract.image_to_string(image, config='--psm 6'))


def analyze_pdf(path):
    pdf = fitz.open(path)
    page_count = len(pdf)
    page_texts = []
    ocr_pages = 0

    for page in pdf:
        text = normalize_text(page.get_text('text'))
        if not usable_text(text):
            text = ocr_page(page)
            ocr_pages += 1
        page_texts.append(text)

    declarations = []
    for page_no, text in enumerate(page_texts, 1):
        for item in parse_chapter_declarations(text):
            item = dict(item)
            item['found_on_page'] = page_no
            declarations.append(item)

    # Handle declarations split between two PDF pages/text blocks.
    for i in range(len(page_texts) - 1):
        combined = normalize_text(page_texts[i] + ' ' + page_texts[i + 1])
        for item in parse_chapter_declarations(combined):
            item = dict(item)
            item['found_on_page'] = i + 1
            declarations.append(item)

    by_chapter = {}
    for item in declarations:
        if item['start'] <= page_count and item['end'] <= page_count:
            by_chapter.setdefault(item['chapter'], {})[(item['start'], item['end'])] = item

    chapters = []
    for chapter in sorted(by_chapter):
        choices = list(by_chapter[chapter].values())
        selected = sorted(choices, key=lambda x: x['found_on_page'])[0]
        selected = dict(selected)
        selected['name'] = f'Chapter {chapter}'
        chapters.append(selected)

    pdf.close()
    return {'page_count': page_count, 'ocr_pages': ocr_pages, 'chapters': chapters}


def sanitize_filename(name):
    name = re.sub(r'[^\w\s-]', '', name, flags=re.UNICODE)
    name = re.sub(r'\s+', '_', name.strip())
    return name or 'Chapter'


HTML = '''<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>VIP Smart Chapter PDF Builder</title>
<style>
*{box-sizing:border-box}body{margin:0;font-family:Arial,sans-serif;background:#f2ecdd;color:#1e2a3f;padding:25px}
.wrap{max-width:1150px;margin:auto}.head{background:#1e2a3f;color:white;padding:25px;border-radius:6px;margin-bottom:20px;display:flex;justify-content:space-between;gap:15px;align-items:center}.head h1{margin:0;font-size:25px}.head p{margin:6px 0 0;color:#c8d0dc;font-size:13px}.badge{border:1px solid #728097;padding:7px 12px;border-radius:4px;font-size:12px}.card{background:#fbf8f0;border:1px solid #d8cfb6;border-radius:5px;padding:24px;margin-bottom:20px}.card h2{margin:0 0 16px;font-size:19px}.uploads{display:grid;grid-template-columns:1fr 1fr;gap:18px}.upload{border:2px dashed #d8cfb6;padding:32px 20px;text-align:center;border-radius:5px;cursor:pointer}.upload:hover,.upload.loaded{border-color:#4c6b53;background:#f5f5eb}.upload input{display:none}.upload b{display:block;margin-bottom:8px}.file{font-size:13px;color:#4c6b53;margin-top:10px;font-weight:bold}.actions{display:flex;gap:10px;flex-wrap:wrap;margin-top:18px}button{padding:11px 17px;border:0;border-radius:4px;font-weight:bold;cursor:pointer}.primary{background:#1e2a3f;color:white}.gold{background:#c9a84c;color:#1e2a3f}.secondary{background:white;border:1px solid #d8cfb6;color:#1e2a3f}button:disabled{opacity:.45;cursor:not-allowed}.hidden{display:none}.status{display:none;margin-top:15px;padding:12px;border-radius:4px;font-size:13px}.status.show{display:block}.success{background:#dce9da;color:#29452e}.error{background:#f3d8d1;color:#8e2d20}.info{background:#e2e8f0;color:#29384e}.summary{display:grid;grid-template-columns:repeat(3,1fr);gap:10px;margin-bottom:18px}.summary div{background:#f5f1e6;border:1px solid #d8cfb6;padding:13px;border-radius:4px}.summary b{display:block;font-size:18px}.summary span{font-size:11px;color:#4d5a70}table{width:100%;border-collapse:collapse}th{background:#1e2a3f;color:white;padding:11px;text-align:left;font-size:12px}td{padding:10px;border-bottom:1px dashed #d8cfb6}input[type=text]{width:100%;padding:9px;border:1px solid #d8cfb6;border-radius:4px}.range{max-width:150px}.loader{position:fixed;inset:0;background:rgba(30,42,63,.72);display:none;align-items:center;justify-content:center;z-index:10}.loader.show{display:flex}.loaderbox{background:#fbf8f0;padding:30px;border-radius:6px;width:min(420px,90%);text-align:center}.spin{width:42px;height:42px;border:4px solid #d8cfb6;border-top-color:#c9a84c;border-radius:50%;animation:spin .8s linear infinite;margin:0 auto 15px}@keyframes spin{to{transform:rotate(360deg)}}@media(max-width:700px){body{padding:12px}.uploads,.summary{grid-template-columns:1fr}.head{align-items:flex-start;flex-direction:column}table{font-size:12px}}
</style></head>
<body>
<div class="loader" id="loader"><div class="loaderbox"><div class="spin"></div><h2 id="loadTitle">Working...</h2><p id="loadText">Please wait</p></div></div>
<div class="wrap">
<div class="head"><div><h1>VIP Smart Chapter PDF Builder</h1><p>Question Paper + Key Answer → chapter-wise PDFs</p></div><div class="badge" id="badge">READY</div></div>
<div class="card"><h2>01 — Select PDFs</h2><div class="uploads">
<label class="upload" id="qbox"><input type="file" id="qfile" accept=".pdf"><b>Question Paper PDF</b><span>Click to choose PDF</span><div class="file" id="qname"></div></label>
<label class="upload" id="abox"><input type="file" id="afile" accept=".pdf"><b>Key Answer PDF</b><span>Click to choose PDF</span><div class="file" id="aname"></div></label>
</div><div class="actions"><button class="primary" id="analyze" disabled>Analyze Chapters</button><button class="secondary" id="reset">Reset</button></div><div id="status" class="status"></div></div>
<div class="card hidden" id="review"><h2>02 — Review Detected Page Ranges</h2><p style="font-size:13px;color:#4d5a70">The numbers below are <b>PDF page numbers</b>. If a page belongs to two chapters, the same page is intentionally used in both chapter PDFs.</p>
<div class="summary"><div><b id="qp">0</b><span>Question Paper Pages</span></div><div><b id="ap">0</b><span>Key Answer Pages</span></div><div><b id="cc">0</b><span>Matched Chapters</span></div></div>
<div style="overflow:auto"><table><thead><tr><th>Chapter</th><th>Question Paper Pages</th><th>Key Answer Pages</th><th>Detected From</th></tr></thead><tbody id="rows"></tbody></table></div>
<div class="actions"><button class="gold" id="generate">Generate PDFs + ZIP</button></div></div>
<div class="card hidden" id="result"><h2>03 — Ready</h2><div id="files"></div><div class="actions"><button class="gold" id="download">Download ZIP</button></div></div>
</div>
<script>
const S={q:null,a:null,chapters:[],zip:null};
const $=x=>document.getElementById(x);
function loader(t,m){$('loadTitle').textContent=t;$('loadText').textContent=m;$('loader').classList.add('show')};function hideLoader(){$('loader').classList.remove('show')}
function msg(t,c){$('status').className='status show '+c;$('status').textContent=t}
function esc(s){return String(s??'').replace(/[&<>"']/g,m=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#039;'}[m]))}
function canAnalyze(){$('analyze').disabled=!(S.q&&S.a)}
$('qfile').onchange=e=>{S.q=e.target.files[0]||null;$('qname').textContent=S.q?S.q.name:'';$('qbox').classList.toggle('loaded',!!S.q);canAnalyze()};
$('afile').onchange=e=>{S.a=e.target.files[0]||null;$('aname').textContent=S.a?S.a.name:'';$('abox').classList.toggle('loaded',!!S.a);canAnalyze()};
$('reset').onclick=()=>location.reload();
$('analyze').onclick=async()=>{const f=new FormData();f.append('question_pdf',S.q);f.append('answer_pdf',S.a);loader('Analyzing PDFs','Reading text and OCR-ing scanned pages...');$('badge').textContent='ANALYZING';try{const r=await fetch('/analyze',{method:'POST',body:f});const d=await r.json();if(!r.ok)throw Error(d.error||'Analysis failed');S.chapters=d.chapters||[];$('qp').textContent=d.question.page_count;$('ap').textContent=d.answer.page_count;$('cc').textContent=S.chapters.length;const rows=$('rows');rows.innerHTML='';S.chapters.forEach((c,i)=>{const tr=document.createElement('tr');tr.innerHTML=`<td><input type="text" data-i="${i}" data-f="name" value="${esc(c.name)}"></td><td><input class="range" type="text" data-i="${i}" data-f="q" value="${c.q_start}-${c.q_end}"></td><td><input class="range" type="text" data-i="${i}" data-f="a" value="${c.a_start}-${c.a_end}"></td><td style="font-size:11px;color:#4d5a70">${esc(c.source)}</td>`;rows.appendChild(tr)});$('review').classList.remove('hidden');$('result').classList.add('hidden');msg(S.chapters.length?`Detected ${S.chapters.length} matched chapter(s). Review before generating.`:'No matched chapters detected.',''+(S.chapters.length?'success':'error'));$('badge').textContent='REVIEW'}catch(e){msg('Error: '+e.message,'error');$('badge').textContent='ERROR'}finally{hideLoader()}};
$('rows').oninput=e=>{const el=e.target,i=+el.dataset.i,f=el.dataset.f;if(!S.chapters[i])return;if(f==='name')S.chapters[i].name=el.value;else{const m=el.value.match(/^(\d+)\s*[-–—]\s*(\d+)$/);if(m){S.chapters[i][f+'_start']=+m[1];S.chapters[i][f+'_end']=+m[2]}}};
$('generate').onclick=async()=>{const f=new FormData();f.append('question_pdf',S.q);f.append('answer_pdf',S.a);f.append('chapters',JSON.stringify(S.chapters));loader('Generating Chapter PDFs','Combining Question Paper pages with Key Answer pages...');$('badge').textContent='BUILDING';try{const r=await fetch('/generate',{method:'POST',body:f});if(!r.ok){let d={};try{d=await r.json()}catch(_){}throw Error(d.error||'Generation failed')}const b=await r.blob();S.zip=URL.createObjectURL(b);$('files').innerHTML=S.chapters.map(c=>`<div style="padding:9px;border-bottom:1px dashed #d8cfb6">✓ ${esc(c.name)}.pdf</div>`).join('');$('result').classList.remove('hidden');msg('Chapter PDFs generated successfully.','success');$('badge').textContent='COMPLETE'}catch(e){msg('Error: '+e.message,'error');$('badge').textContent='ERROR'}finally{hideLoader()}};
$('download').onclick=()=>{if(!S.zip)return;const a=document.createElement('a');a.href=S.zip;a.download='chapter-wise-pdfs.zip';a.click()};
</script></body></html>'''


@app.route("/main1")
def main1():
    return render_template_string(HTML_TEMPLATE)


@app.route('/analyze', methods=['POST'])
def analyze():
    q = request.files.get('question_pdf')
    a = request.files.get('answer_pdf')
    if not q or not a:
        return jsonify({'error': 'Please upload both Question Paper and Key Answer PDFs.'}), 400
    if not allowed_file(q.filename) or not allowed_file(a.filename):
        return jsonify({'error': 'Only PDF files are allowed.'}), 400

    qpath = apath = None
    try:
        qfd, qpath = tempfile.mkstemp(suffix='.pdf'); os.close(qfd)
        afd, apath = tempfile.mkstemp(suffix='.pdf'); os.close(afd)
        q.save(qpath); a.save(apath)

        qr = analyze_pdf(qpath)
        ar = analyze_pdf(apath)
        qm = {x['chapter']: x for x in qr['chapters']}
        am = {x['chapter']: x for x in ar['chapters']}
        chapters = []
        for n in sorted(set(qm) & set(am)):
            x, y = qm[n], am[n]
            chapters.append({
                'chapter': n, 'name': f'Chapter {n}',
                'q_start': x['start'], 'q_end': x['end'],
                'a_start': y['start'], 'a_end': y['end'],
                'source': f"Q: {x['source']} | A: {y['source']}"
            })

        return jsonify({'question': {'page_count': qr['page_count'], 'ocr_pages': qr['ocr_pages'], 'detected': qr['chapters']}, 'answer': {'page_count': ar['page_count'], 'ocr_pages': ar['ocr_pages'], 'detected': ar['chapters']}, 'chapters': chapters})
    except pytesseract.TesseractNotFoundError:
        return jsonify({'error': 'Tesseract OCR is not installed. Add tesseract-ocr to the Render system build.'}), 500
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        for p in (qpath, apath):
            if p and os.path.exists(p):
                try: os.unlink(p)
                except OSError: pass


@app.route('/generate', methods=['POST'])
def generate():
    q = request.files.get('question_pdf')
    a = request.files.get('answer_pdf')
    raw = request.form.get('chapters', '')
    if not q or not a or not raw:
        return jsonify({'error': 'Question PDF, Key Answer PDF and chapter data are required.'}), 400
    try:
        chapters = json.loads(raw)
        if not isinstance(chapters, list) or not chapters:
            raise ValueError('No chapters supplied.')
    except Exception as e:
        return jsonify({'error': f'Invalid chapter data: {e}'}), 400

    qpath = apath = outdir = None
    try:
        qfd, qpath = tempfile.mkstemp(suffix='.pdf'); os.close(qfd)
        afd, apath = tempfile.mkstemp(suffix='.pdf'); os.close(afd)
        q.save(qpath); a.save(apath)
        qr, ar = PdfReader(qpath), PdfReader(apath)
        outdir = tempfile.mkdtemp(prefix='vip_chapters_')
        names = []

        for i, c in enumerate(chapters, 1):
            name = str(c.get('name') or f'Chapter {i}').strip()
            try:
                qs, qe = int(c['q_start']), int(c['q_end'])
                ass, ae = int(c['a_start']), int(c['a_end'])
            except Exception:
                return jsonify({'error': f'Invalid range for {name}.'}), 400
            if not (1 <= qs <= qe <= len(qr.pages)):
                return jsonify({'error': f'{name}: Question Paper range {qs}-{qe} is outside 1-{len(qr.pages)}.'}), 400
            if not (1 <= ass <= ae <= len(ar.pages)):
                return jsonify({'error': f'{name}: Key Answer range {ass}-{ae} is outside 1-{len(ar.pages)}.'}), 400

            writer = PdfWriter()
            # Exact ranges are copied. If ranges overlap, the overlapping page is copied again.
            for p in range(qs - 1, qe): writer.add_page(qr.pages[p])
            for p in range(ass - 1, ae): writer.add_page(ar.pages[p])

            filename = sanitize_filename(name) + '.pdf'
            path = os.path.join(outdir, filename)
            with open(path, 'wb') as f: writer.write(f)
            names.append(filename)

        buf = BytesIO()
        with zipfile.ZipFile(buf, 'w', zipfile.ZIP_DEFLATED) as z:
            for name in names: z.write(os.path.join(outdir, name), arcname=name)
        buf.seek(0)
        return send_file(buf, mimetype='application/zip', as_attachment=True, download_name='chapter-wise-pdfs.zip')
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        for p in (qpath, apath):
            if p and os.path.exists(p):
                try: os.unlink(p)
                except OSError: pass
        if outdir and os.path.isdir(outdir):
            for name in os.listdir(outdir):
                try: os.unlink(os.path.join(outdir, name))
                except OSError: pass
            try: os.rmdir(outdir)
            except OSError: pass


@app.route('/health')
def health():
    return jsonify({'status': 'healthy', 'service': 'VIP Smart Chapter PDF Builder'})


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
