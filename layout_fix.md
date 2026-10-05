# layout_fix.md: make the KAK Generator bot output match `KAK_example.pdf`

## 0. Context

- This project is a **KAK Generator bot**. It takes inputs and produces a KAK (Kerangka Acuan Kerja) PDF. The PDF `Producer` field of a bot sample says **xhtml2pdf**, so rendering is HTML/CSS to PDF through xhtml2pdf.
- **There is no "target file" to patch.** The fix is in the bot: its HTML/CSS template(s), its data-to-HTML code and any helper functions (dates, numbers, lists).
- **`KAK_example.pdf` is the gold standard.** Every KAK the bot produces must look like it: layout, fixed text, and conventions for formatting values.
- `KAK_Belanja_Jasa_Konsultansi_Penyusunan_Base_05-10-2026_093610.pdf` is a sample of the bot's **current (wrong) output** for a different job. Use it as the "before" example only.
- **What may vary:** the user's input data (job title, text, lists, amounts, durations, personnel, dates). **What must not vary:** page setup, fonts, geometry, row labels, fixed sentences, value formats, table structure.
- Measurements are PDF points (pt), 1 in = 72 pt, measured from the reference with pdfplumber. Tolerance about ±2 pt for positions and ±1 pt for column edges.
- Priority tags: **P0** = must fix. **P1** = should fix. **P2** = polish.

---

## 1. Summary of what the bot gets wrong

1. **P0** Page size is A4 (595 × 842 pt). Reference: **612 × 936 pt** (8.5 × 13 in, F4/Folio).
2. **P0** Cover letterhead image is embedded but rendered at **0 × 0 pt**, so it is invisible.
3. **P0** Schedule (row 14) is bullets. Reference: **15-column Gantt table** with shaded cells and footnotes, computed from a start date.
4. **P0** Personnel table (row 13) has 4 equal columns, no "No" column, and text overflows the cells.
5. **P0** Body text is left-aligned with tight spacing. Reference: **justified, 19 pt line pitch**.
6. **P0** Every row has 22–55 pt of dead space, which pushes row 17 alone onto a nearly empty page.
7. **P0** **"Nomor" month is numeric (`/10/`).** Reference: **Roman numeral** (`/X/`). This is the standard, so it is a bot bug.
8. **P1** Lists are typed hyphens (`- item`). Reference: **`1)` / `a)` lists** with hanging indents.
9. **P1** Cover has wrong font sizes (11 pt vs 12/13 pt), wrong vertical rhythm, wrong table geometry.
10. **P1** Many row labels and fixed sentences differ from the reference (section 6).
11. **P1** Value formats differ: `Rp 100,000,000` vs `Rp100.000.000 (seratus juta rupiah)`; `90 hari` vs `90 (sembilan puluh) hari`.
12. **P1** Literal `None` printed in row 10, which means null fields are not handled.
13. **P1** Fonts are not embedded (base-14 Times-Roman/Helvetica). Reference embeds Times New Roman.
14. **P2** Metadata, and the cover title/package wording pattern (section 4.4).

---

## 2. Page setup (P0)

| Property | Value |
|---|---|
| Page size | **612 × 936 pt** (8.5 in × 13 in) on every page |
| Content box | x = 73 → 541 (**468 pt** wide) |
| Margins | left 73, right 71, top 73, bottom 73 pt |
| Header / footer / page numbers | None |

```css
@page { size: 612pt 936pt; margin: 73pt 71pt 73pt 73pt; }
```

Check with `pdfinfo`: `Page size: 612 x 936 pts`.

## 3. Typography (P0)

| Property | Value |
|---|---|
| Font | **Times New Roman**, regular + bold, **embedded**. Register `times.ttf` and `timesbd.ttf` with `@font-face` (ship them with the bot, or use **Liberation Serif**, which is metric-compatible). No base-14 fallback. |
| Body size | 11 pt |
| Body line height | **19 pt** |
| Paragraph gap | **10 pt** between paragraphs in a cell (line pitch 19 pt inside, 29 pt across) |
| Alignment | **justified** for body paragraphs and list item text. Short single-line items (such as "Lokasi Pekerjaan: …") naturally look left-aligned. |
| Bold | row labels, row numbers, table headers, cover text |
| Italic | none |

```css
@font-face { font-family: "TNR"; src: url("fonts/times.ttf"); }
@font-face { font-family: "TNR"; src: url("fonts/timesbd.ttf"); font-weight: bold; }
body { font-family: "TNR", "Liberation Serif", serif; font-size: 11pt; line-height: 19pt; }
p    { margin: 0 0 10pt 0; text-align: justify; }
```

---

## 4. Cover page

### 4.1 Letterhead image (P0)
- Give the `<img>` an **explicit size in pt**: **468 × 151 pt**, positioned at **x 74 → 542, y 74 → 225**. The reference stretches the image slightly, so use these exact numbers. The asset (658 × 180 px JPEG) is already in the bot.
- Verify: `pdfplumber` → `page.images[0]` bbox ≈ (74, 74, 542, 225).

### 4.2 Title block (P1)
Centered, **bold 12 pt**, text tops at y ≈ 273 / 301 / 329 / 356:

1. `KERANGKA ACUAN KERJA (KAK)` (constant)
2. `JASA KONSULTANSI` (constant)
3. `{PAKET}` (variable; see 4.4)
4. `KOTA YOGYAKARTA` (constant, or the city if the bot supports other cities)

Line height 14 pt, plus one blank line (14 pt) after each line, for a pitch of about 27.7 pt. No larger gaps (current output has about 40 pt).
The block starts about 48 pt below the letterhead.

### 4.3 "Nomor" line (P0 and P1)
- Centered, **bold 13 pt** (larger than the title), text top y ≈ **425**.
- Format: `Nomor : {seq}/KAK-KAJIAN-{xx}/{BULAN_ROMAWI}/{TAHUN}`, for example `Nomor : 004/KAK-KAJIAN-04/X/2026`.
- **The month segment must be a Roman numeral, uppercase** (the standard for Indonesian document numbers): 1=I, 2=II, 3=III, 4=IV, 5=V, 6=VI, 7=VII, 8=VIII, 9=IX, 10=X, 11=XI, 12=XII.
- Keep whatever the bot currently does for `{seq}`, `{xx}` and the year. Change **only** the month segment.

```python
ROMAN = ["I","II","III","IV","V","VI","VII","VIII","IX","X","XI","XII"]
def roman_month(m: int) -> str:
    return ROMAN[m - 1]
```

### 4.4 Info table (P1)
Borderless, 3 columns: label **96 pt** (73 → 169), colon **15 pt** (169 → 184), value **357 pt** (184 → 541).
Table top y ≈ **487**, bottom y ≈ **654**. All text **bold 12 pt, uppercase**, line height **14 pt**, cell padding about 4 pt left, row spacing about 11 pt (so row height = lines × 14 + 11 → rows of **25 / 39 / 52 / 25 / 25 pt** in the reference).
Value column is **justified**. Label text starts at x ≈ 77.2, value text at x ≈ 189.

| Row | Label | Value |
|---|---|---|
| 1 | `KEGIATAN` | `KEGIATAN PENGELOLAAN PENDAPATAN DAERAH` (variable) |
| 2 | `SUB` ⏎ `KEGIATAN` (**two lines**: force with `<br>`) | `ANALISA DAN PENGEMBANGAN PAJAK DAERAH, SERTA PENYUSUNAN KEBIJAKAN PAJAK DAERAH` (variable) |
| 3 | `PEKERJAAN` | `BELANJA JASA KONSULTANSI KAJIAN PENDAPATAN ASLI DAERAH (JASA KONSULTANSI {PAKET})` |
| 4 | `PAKET` | `{PAKET}` |
| 5 | `NO DPA` | `DPA/A.1/5.02.0.00.0.00.01.0000/001/2026` (variable) |

**Package-name rule (inferred from one pair of examples; confirm with the user).**
- Reference: `PAKET` = `PENYUSUNAN BASIS DATA PENDAPATAN ASLI DAERAH`, and the cover title line 3 is the same value. `PEKERJAAN` embeds it as `(JASA KONSULTANSI PENYUSUNAN BASIS DATA …)`.
- Current bot: the package value already contains the prefix `BELANJA JASA KONSULTANSI`. This produces a duplicated, longer title and `(BELANJA JASA KONSULTANSI …)` in PEKERJAAN.
- Fix: strip a leading `BELANJA JASA KONSULTANSI` from the package name and use the stripped value for title line 3, `PAKET`, and the `PEKERJAAN` parentheses. Keep the full original name for anything that needs it (for example the output filename).

### 4.5 Bottom text (P1)
`TAHUN ANGGARAN {tahun}`, centered, **bold 13 pt**, text top y ≈ **719**.

---

## 5. Main 17-row table: geometry (P0 and P1)

| Column | x-range | Width |
|---|---|---|
| No | 73 → 106 | **33 pt** |
| Label | 106 → 232 | **126 pt** |
| Content | 232 → 541 | **309 pt** |

- Total **468 pt**. Current widths are 24 / 120 / 338.
- Borders: thin solid black grid (0.5–0.75 pt). Cell padding about 4–5 pt left, 6 pt right, 4 pt top.
- **Number column:** bold, **right-aligned** (glyph right edge about 6 pt from the cell edge). **Label column:** bold, left-aligned. **Content column:** justified. All cells vertically **top**.
- **Row height hugs content. No dead space (P0).** Remove whatever creates it in the bot: trailing empty `<p>`, trailing `<br>`, fixed `height`/`min-height`, bottom margin on the last paragraph. Last paragraph in a cell has `margin-bottom: 0`.
- Rows **can split across pages** in the reference. xhtml2pdf generally breaks only between rows. Where that blocks parity, rely on the tighter rows (the reference is 7 pages; the bot should land near that). Do not force a page break before each row. Only the Gantt row should use `page-break-inside: avoid`.

---

## 6. Row labels (constants) and row structures

Labels are **bold**, and must be exactly these strings (the bot currently shortens several):

| # | Label | Content structure | List spacing |
|---|---|---|---|
| 1 | Latar Belakang | 1 or more justified paragraphs, 10 pt apart | n/a |
| 2 | Maksud dan Tujuan | `1) Maksud`, then an indented paragraph, then `2) Tujuan`, then level-2 list `a) b) c) …` | **loose** (10 pt) |
| 3 | Sasaran | `1) 2) 3) …` | tight |
| 4 | Lokasi Kegiatan | plain paragraph: `Pekerjaan ini berlokasi di {lokasi}` | n/a |
| 5 | Sumber Pendanaan dan Perkiraan Biaya | `1)` `Kegiatan ini dibiayai dari sumber pendanaan Anggaran Pendapatan dan Belanja Daerah (APBD) Pemerintah Kota Yogyakarta Tahun Anggaran {tahun}.` `2)` `Total Perkiraan biaya yang diperlukan paling banyak Rp{jumlah} ({terbilang} rupiah), sudah termasuk PPN 11%.` | tight |
| 6 | Ruang Lingkup, Lokasi Pekerjaan, Fasilitas Penunjang | line `Ruang Lingkup Pekerjaan:`, numbered list, then line `Lokasi Pekerjaan: {lokasi}`, then line `Fasilitas Penunjang: {fasilitas}` | tight |
| 7 | Hasil Produk | `1) 2) 3) …` | tight |
| 8 | Waktu Pelaksanaan | `Durasi pekerjaan adalah {N} ({terbilang}) hari kalender sejak SPMK.` | n/a |
| 9 | Pendekatan dan Metodologi | lead-in `Pekerjaan ini akan menggunakan beberapa pendekatan untuk dapat menghasilkan produk yang diharapkan.`, then `1) Pendekatan Kualitatif, meliputi:` with level-2 `a) b) …`, then `2) Pendekatan Kuantitatif, meliputi:` with level-2 list, then (optional) closing paragraph + diagram (section 12) | tight |
| 10 | Spesifikasi Teknis | `1) 2) …` | **loose** |
| 11 | Peralatan dan Material | `1) 2) …` | **loose** |
| 12 | Jangka Waktu Penyelesaian Pekerjaan | `Jangka waktu penyelesaian pekerjaan {paket} adalah {N} ({terbilang}) hari kalender terhitung sejak ditandatanganinya Surat Perjanjian Kontrak (SPK).` | n/a |
| 13 | Kebutuhan Personil | lead-in + nested table (section 9) | n/a |
| 14 | Jadwal Pelaksanaan Pekerjaan | lead-in + merged full-width row with Gantt (section 10) | n/a |
| 15 | Laporan Akhir | lead-in `Laporan akhir sekurang-kurangnya memuat substansi sebagai berikut:`, then `1) … 10)` | tight |
| 16 | Pedoman Pengumpulan Data Lapangan | lead-in `Pengumpulan data harus memenuhi persyaratan berikut:`, then `1) 2) 3)` | tight |
| 17 | Alih Pengetahuan | `1) 2)` | tight |

Notes:
- `{paket}` in row 12 is the stripped package name in title case (reference text: "Penyusunan Basis Data Pendapatan Asli Daerah Kota Yogyakarta"). Do not duplicate the leading word (the reference has a typo, "Penyusunan Penyusunan"; do not copy it).
- Row 11 lead-in, and similar variable sentences: use the user's text, but keep the **structure** above.
- **Single-item cells** (for example a Sasaran with one item) are a plain paragraph with no marker, like row 4.
- Multi-item cells use the list style in section 7. Keep user-supplied text verbatim, escape HTML (`&` → `&amp;`), and do not add or remove punctuation. The reference is itself not uniform about trailing `;` / `; dan`.

---

## 7. Lists inside cells (P1)

Replace every typed `- item` / `•` / `<br>`-separated item with a real structured list.

| Level | Marker | Marker right edge (x) | Text x |
|---|---|---|---|
| 1 | `1)`, `2)`, … `10)` | **263.4** (≈ +26 from cell content left of 237) | **272.2** (+35) |
| 2 | `a)`, `b)`, … | **≈ 299** | **≈ 308** (+71) |

- Markers are **right-aligned** to the marker right edge. A two-digit marker (`10)`) grows leftwards, and its text still starts at the same text x (see row 15).
- **Hanging indent:** wrapped lines return to the text x, not the left edge.
- Plain paragraphs that belong to a level-1 item (such as the Maksud paragraph) are indented to the text x of that level.
- Spacing: **tight** = 0 pt between items (pitch 19 pt). **Loose** = 10 pt between items (pitch 29 pt). Use the per-row setting in section 6.
- Implement lists as a 2-column structure (a marker cell and a text cell, or equivalent). Do not rely on `list-style-type` for `1)` / `a)`, because xhtml2pdf handles it poorly.
- **Input parsing:** where bot data arrives as a string with `-` / `•` / newline-separated items, split into items before rendering. Do not print the dashes. Where input is already a list, use it as is. The bot should store *Maksud* (paragraph) and *Tujuan* (list) as separate fields.

---

## 8. Value formats (P1)

| Value | Format | Example |
|---|---|---|
| Rupiah | `Rp` directly followed by the number, **dot thousands separator**, **no space**, then the amount in words in parentheses | `Rp100.000.000 (seratus juta rupiah)` |
| Duration | number, then Indonesian words in parentheses | `90 (sembilan puluh) hari kalender` |
| Roman month | in the Nomor line only | `X` |
| Dates | Indonesian weekday and month names, **never locale-dependent** | `Senin, 4 Mei 2026` |

- Write a small `terbilang(n)` helper, or use `num2words(n, lang="id")`. Test: `90` → `sembilan puluh`, `100000000` → `seratus juta`.
- Use explicit arrays for names. Do not use `strftime` or locale settings, which vary by server.
  - Days: Senin, Selasa, Rabu, Kamis, Jumat, Sabtu, Minggu.
  - Months: Januari, Februari, Maret, April, Mei, Juni, Juli, Agustus, September, Oktober, November, Desember.
- **Null handling (bug):** the bot printed the literal `None` in row 10. Never print `None`/`null`/empty strings. Use one consistent fallback for missing fields (`-`, which the bot already uses elsewhere), or ask the user for the missing data.

---

## 9. Row 13: Personnel table (P0)

Cell content: lead-in paragraph `Untuk melaksanakan Pekerjaan ini, personil yang dibutuhkan adalah sebagai berikut:` (justified), then about 17 pt gap, then a nested table.

| Property | Value |
|---|---|
| Position | left edge **x = 237** (content-cell left), width **295 pt** |
| Columns | **5**: `No` · `Posisi` · `Jumlah Tenaga Ahli` · `Kualifikasi Pendidikan Minimal` · `Pengalaman Minimal (Tahun)` |
| Column widths | **25 / 68 / 46 / 91 / 65 pt** (fixed, in pt) |
| Font | **9 pt**, header **bold** |
| Header alignment | centered |
| Body alignment | `No`, `Posisi` left; `Jumlah`, `Kualifikasi`, `Pengalaman` centered |
| Vertical align | top |
| Row heights | header about 42, then about 42 / 32 / 32 (hugging content) |
| Borders | thin black grid |

- `No` is auto-numbered 1..n.
- `Kualifikasi` = degree + field, for example `S2 Ilmu Pemerintahan`. `Pengalaman` is **a number only** (`5`), because the header already says "Tahun". Strip `th` / `tahun` from input.
- **Overflow fix:** long unbreakable tokens (`Ekonomi/Manajemen/Keuangan/Kebijakan Publik`) overflow cells. Before rendering, insert a space after each `/` in table cell text (`Ekonomi / Manajemen / …`) so it wraps inside the 91 pt column.
- Set widths in `pt`. Percentage widths on nested xhtml2pdf tables are unreliable.

---

## 10. Row 14: Schedule as a Gantt table (P0)

### Structure
- **First `<tr>`:** number `14.` | **Jadwal Pelaksanaan Pekerjaan** | lead-in (justified): `Waktu yang dibutuhkan untuk menyelesaikan pekerjaan adalah {N} ({terbilang}) hari kalender dengan Jadwal Rencana Pelaksanaan Kegiatan pada tabel berikut :`
- **Second `<tr>`:** one `<td colspan="3">` spanning x 73 → 541. It holds the Gantt table (left edge x = 78, so 5 pt inside) followed by the footnotes.
- Apply `page-break-inside: avoid` to this whole row.

### Gantt geometry
x **78 → 532** (454 pt wide), 15 columns, about 175 pt tall:

| Col | Content | Width |
|---|---|---|
| 1 | No | **21 pt** |
| 2 | Kegiatan | **87 pt** |
| 3–6, 7–10, 11–14 | week columns, 3 month blocks × 4 weeks | **25.5 pt** each |
| 15 | KET | **40 pt** |

- **Header = 2 rows (about 22 pt each):** Row A: three month names (each `colspan="4"`), centered, **8 pt**. Row B: `I II III IV` repeated, centered, **5.5 pt**. The `No` and `Kegiatan` header cells are empty. `KET` is **rowspan 2**, centered, **7.5 pt**.
- **Body: 6 rows**, 8 pt, `KET` 7.5 pt, left-aligned text, top vertical align. Heights in the reference: **29** (row 1, wraps to two lines), then **20, 21, 20, 20, 21**.
- Thin black grid. Shade color **`#B7B7B7`**.

### Body rows (constants)
`No` / `Kegiatan` / KET:

| No | Kegiatan | KET |
|---|---|---|
| 1 | Penandatanganan Kontrak | (empty) |
| 2 | Pelaksanaan Pekerjaan | (empty) |
| (empty) | - Laporan Pendahuluan | `30 Hari` |
| (empty) | - Laporan Antara | `60 Hari` |
| (empty) | - Laporan Akhir | `{N} Hari` |
| 3 | Serah Terima Pekerjaan | `{N} Hari` |

### Computed content (generate from start date and duration)
Reference case: start **Senin, 4 Mei 2026**, **N = 90** days.

- **Month headers:** the start month and the next two months, uppercase: `MEI`, `JUNI`, `JULI`.
- **Week columns:** 12 columns, each worth 7.5 days. Column for a day `d` = `ceil(d / 7.5)`.
- **Shading (17 cells, X = shaded):**

| Row | Shaded columns (1–12) |
|---|---|
| Penandatanganan Kontrak | 1 |
| Pelaksanaan Pekerjaan | 1–12 (all 12) |
| - Laporan Pendahuluan | 4 (day 30) |
| - Laporan Antara | 8 (day 60) |
| - Laporan Akhir | 12 (day N) |
| Serah Terima Pekerjaan | 12 |

Total = 1 + 12 + 1 + 1 + 1 + 1 = **17** shaded cells.
(Columns 1–4 are MEI I–IV, 5–8 JUNI I–IV, 9–12 JULI I–IV.)

- Only the **90-day** case is verified by the reference. For other durations, generalize with `ceil(N/30)` month blocks of 4 weeks and the same 30/60/N markers, and flag that this is unverified.
- The bot needs a **start date** input. If it does not have one, add it (suggested default: the next Monday).

### Footnotes (9 pt, justified, line pitch about 10.3 pt, left x ≈ 82.5, right x ≈ 528; below the table in the same cell)
Templates, reproduced from the reference:

1. `*Mulai pada {hari}, {tgl} {bulan} {tahun}`
2. `*Batas Akhir ({N} hari) adalah {hari_akhir}, {tgl_akhir} {bulan_akhir} {tahun_akhir}.`
3. `*Serah Terima Pekerjaan: Karena {tgl_akhir} {bulan_akhir} adalah hari {hari_akhir}, Anda dapat memajukan serah terima menjadi {Jumat}, {tgl} {bulan} {tahun} (berjalan {N-1} hari). Hal ini diperbolehkan karena {N} hari adalah batas maksimal penyelesaian, dan ini sangat sejajar dengan arsiran minggu keempat bulan {bulan_terakhir}.`

- End date = start date + (N − 1) days. (Check: 4 May + 89 = 1 Aug.)
- Note 3 appears **only when the end date is a weekend**. For Saturday, handover moves to the previous Friday (`berjalan 89 hari`). For Sunday, to the previous Friday (`berjalan 88 hari`). For a weekday end date, omit note 3 (assumption, flag it).
- Wording in note 3 is copied from the reference for parity. See section 13 about its tone.

---

## 11. Known bot bugs to fix along the way (P1)

| Bug | Fix |
|---|---|
| Letterhead `<img>` renders at 0 × 0 | Explicit pt size (4.1) |
| Roman-numeral month missing in Nomor | 4.3 |
| Literal `None` printed | Null handling (section 8) |
| Hyphen strings printed as text | Parse into lists (section 7) |
| Currency/duration without terbilang and Indonesian separators | Section 8 |
| Shortened labels (`Jangka Waktu`, `Metodologi`, `Jadwal Pelaksanaan`, …) | Exact labels (section 6) |
| Row 6 missing `Lokasi Pekerjaan` / `Fasilitas Penunjang` lines | Add as in section 6 |
| Package name includes `BELANJA JASA KONSULTANSI` | Strip it (4.4) |

---

## 12. Row 9 diagram (optional)

The reference's row 9 ends with a closing paragraph and a flowchart image (298 × 176 pt, about 179 ppi, left-aligned at the cell content left, placed after the paragraph). It is specific to the reference's content. **Default: do not generate it.** If the bot gets (or already has) a diagram for the methodology, place it as described. Do not invent one.

---

## 13. Decisions and defaults (report which you applied)

| Item | Default |
|---|---|
| Yellow highlight (`#FFFF00`) on the row 14 label cell in the reference | **Off**: looks like a leftover editing mark. Put it behind a single constant so it is easy to enable. |
| Footnote 3 wording ("Anda dapat memajukan…") | Verbatim, as in the reference. It reads like a conversational drafting note, so flag it to the user as a possible wording change. |
| PDF metadata title | Set a meaningful title (the reference's "Workflow Pengadaan Langsung" is a leftover; do not copy it) |
| Reference typo "Penyusunan Penyusunan" in row 12 | Do not copy |
| Row splitting across pages | If xhtml2pdf cannot split inside a row, accept row-boundary breaks and report it. Propose WeasyPrint or Chromium only if the user wants exact parity. |

---

## 14. Starter CSS (adapt to the existing templates)

```css
@page { size: 612pt 936pt; margin: 73pt 71pt 73pt 73pt; }
@font-face { font-family: "TNR"; src: url("fonts/times.ttf"); }
@font-face { font-family: "TNR"; src: url("fonts/timesbd.ttf"); font-weight: bold; }

body { font-family: "TNR", "Liberation Serif", serif; font-size: 11pt; line-height: 19pt; }
p    { margin: 0 0 10pt 0; text-align: justify; }
p.last { margin-bottom: 0; }

table.main { width: 468pt; border-collapse: collapse; }
table.main td { border: 0.75pt solid #000; vertical-align: top; padding: 4pt 6pt 4pt 5pt; }
td.no    { width: 33pt;  font-weight: bold; text-align: right; }
td.label { width: 126pt; font-weight: bold; text-align: left; }
td.body  { width: 309pt; text-align: justify; }

table.personnel { width: 295pt; border-collapse: collapse; font-size: 9pt; line-height: 11pt; }
table.gantt     { width: 454pt; border-collapse: collapse; font-size: 8pt; line-height: 10pt; }
td.shade { background-color: #B7B7B7; }
.footnote { font-size: 9pt; line-height: 10.3pt; text-align: justify; margin: 0; }

img.letterhead { width: 468pt; height: 151pt; }
```

xhtml2pdf cautions: set `line-height` in `pt`; set nested table widths in `pt`; `:last-child` support is limited, so use a `.last` class; confirm fonts with `pdffonts` (`emb: yes`); check image sizes in the output PDF, not just in the HTML.

---

## 15. Test plan and acceptance checklist

### Golden test (do this first)
Rebuild the **input data of `KAK_example.pdf`** (its text, lists, amounts, personnel, start date 4 Mei 2026, 90 days) and feed it to the bot. The result should match `KAK_example.pdf` within the tolerances above: about 7 pages, same row labels, same Gantt shading, same cover geometry. Keep this as a regression test.

### Checks to run on any generated PDF
```bash
pdfinfo out.pdf | grep "Page size"      # → 612 x 936 pts
pdffonts out.pdf                         # → Times New Roman / Liberation Serif, emb = yes
```

```python
import pdfplumber
pdf = pdfplumber.open("out.pdf")

print([(round(i['x0']), round(i['top']), round(i['x1']), round(i['bottom']))
       for i in pdf.pages[0].images])                  # ≈ (74, 74, 542, 225)

t = pdf.pages[1].find_tables()[0]
print(sorted({round(c[0]) for r in t.rows for c in r.cells if c} |
             {round(c[2]) for r in t.rows for c in r.cells if c}))   # ≈ [73, 106, 232, 541]

print(sum(1 for pg in pdf.pages for r in pg.rects
          if r.get('non_stroking_color') == (0.7176, 0.7176, 0.7176)))   # 17 for a 90-day job
```

### Checklist
- [ ] Page size 612 × 936 pt, all pages
- [ ] Fonts embedded, no Helvetica / base-14 Times-Roman
- [ ] Cover: letterhead visible; title tops ≈ 273 / 301 / 329 / 356; "Nomor" and "TAHUN ANGGARAN" at 13 pt; info table 96 / 15 / 357 pt; "SUB / KEGIATAN" on two lines
- [ ] Nomor month is a Roman numeral (for example `/X/`)
- [ ] Title line 3, `PAKET` and `PEKERJAAN` use the stripped package name (no duplicated `BELANJA JASA KONSULTANSI`)
- [ ] Main table columns ≈ 73 / 106 / 232 / 541; numbers right-aligned
- [ ] Body justified, 19 pt line pitch, 10 pt paragraph gap
- [ ] No dead space under rows; no nearly empty last page
- [ ] All 17 row labels exactly as in section 6
- [ ] Lists are `1)` / `a)` with right-aligned markers and hanging indents; no leading `- `; tight/loose per row
- [ ] Rupiah and durations in the section 8 format; no literal `None`
- [ ] Personnel table: 5 columns, 9 pt, widths 25 / 68 / 46 / 91 / 65, no overflow
- [ ] Row 14: merged full-width row with a 15-column Gantt, 17 shaded `#B7B7B7` cells (for 90 days), KET values 30 / 60 / N / N Hari, and 9 pt footnotes computed from the start date
- [ ] Row 14 label not highlighted yellow (unless the flag is on)
- [ ] Report pass/fail per item, plus anything blocked by xhtml2pdf
