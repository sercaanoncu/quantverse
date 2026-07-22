import fs from "node:fs/promises";
import { SpreadsheetFile, Workbook } from "@oai/artifact-tool";

const [payloadPath, outputPath] = process.argv.slice(2);
const payload = JSON.parse(await fs.readFile(payloadPath, "utf8"));
const workbook = Workbook.create();
workbook.comments.setSelf({ displayName: "QuantVerse" });

const dark = "#17324D";
const blue = "#2B6F8F";
const light = "#EAF2F6";
const amber = "#F4B942";
const red = "#B54747";

function colLetter(number) {
  let output = "";
  for (let value = number; value >= 0; value = Math.floor(value / 26) - 1) {
    output = String.fromCharCode((value % 26) + 65) + output;
  }
  return output;
}

function applyNumberFormats(sheet, rows, startRow) {
  if (!rows.length) return;
  const headers = rows[0];
  const percentTokens = ["weight", "return", "cagr", "volatility", "drawdown", "var_95", "cvar_95", "turnover", "momentum", "risk_contribution", "ci_lower", "ci_upper", "probability"];
  headers.forEach((header, index) => {
    const key = String(header).toLowerCase();
    if (percentTokens.some((token) => key.includes(token))) {
      const col = colLetter(index);
      sheet.getRange(`${col}${startRow + 1}:${col}${startRow + rows.length - 1}`).format.numberFormat = "0.00%;[Red](0.00%);-";
    }
  });
}

for (const spec of payload.sheets) {
  const sheet = workbook.worksheets.add(spec.name);
  sheet.showGridLines = false;
  const rows = spec.rows.length ? spec.rows : [["status"], ["No rows available"]];
  const width = Math.max(...rows.map((row) => row.length));
  const normalized = rows.map((row) => [...row, ...Array(width - row.length).fill("")]);
  const endCol = colLetter(width - 1);
  sheet.getRange(`A1:${endCol}1`).merge();
  sheet.getRange("A1").values = [[spec.name]];
  sheet.getRange("A1").format = { fill: dark, font: { bold: true, color: "#FFFFFF", size: 15 } };
  sheet.getRange(`A2:${endCol}3`).merge();
  sheet.getRange("A2").values = [[spec.explanation]];
  sheet.getRange("A2").format = { fill: light, font: { color: dark }, wrapText: true };
  sheet.getRangeByIndexes(4, 0, normalized.length, width).values = normalized;
  sheet.getRange(`A5:${endCol}5`).format = { fill: blue, font: { bold: true, color: "#FFFFFF" }, wrapText: true };
  const dataRange = sheet.getRange(`A5:${endCol}${4 + normalized.length}`);
  dataRange.format.autofitColumns();
  dataRange.format.autofitRows();
  dataRange.format.borders = { preset: "insideHorizontal", style: "thin", color: "#D7E0E5" };
  applyNumberFormats(sheet, normalized, 5);
  sheet.freezePanes.freezeRows(5);
  sheet.getRange(`A5:${endCol}${4 + normalized.length}`).format.wrapText = true;
  for (let col = 0; col < width; col += 1) {
    const range = sheet.getRange(`${colLetter(col)}5:${colLetter(col)}${4 + normalized.length}`);
    const header = String(normalized[0][col] ?? "").toLowerCase();
    range.format.columnWidthPx = Math.min(header.includes("reason") || header.includes("limitation") || header.includes("formula") || header.includes("interpretation") ? 300 : 145, 300);
  }
  if (spec.name === "START_HERE") {
    sheet.getRange("A5:A13").format = { fill: light, font: { bold: true, color: dark }, wrapText: true, columnWidthPx: 230 };
    sheet.getRange("B5:B13").format = { wrapText: true, columnWidthPx: 720 };
  }
  if (spec.name === "CURRENT_PORTFOLIO") {
    sheet.getRange("B5:B25").format.columnWidthPx = 240;
    sheet.getRange("F5:F25").format.columnWidthPx = 230;
  }
  if (spec.name === "HOLDING_RATIONALE") {
    sheet.getRange("B5:B25").format.columnWidthPx = 235;
    sheet.getRange("J5:J25").format.columnWidthPx = 330;
  }
  if (spec.name === "REJECTED_CANDIDATES") {
    sheet.getRange("B5:B25").format.columnWidthPx = 270;
    sheet.getRange("C5:C25").format.columnWidthPx = 190;
    sheet.getRange("D5:D25").format.columnWidthPx = 145;
    sheet.getRange("E5:F25").format.columnWidthPx = 300;
  }
  if (spec.name === "DATA_QUALITY") {
    sheet.getRange("A5:A14").format.columnWidthPx = 270;
  }
  if (spec.name === "LIMITATIONS") {
    sheet.getRange("A5:A12").format.columnWidthPx = 150;
    sheet.getRange("B5:B12").format.columnWidthPx = 520;
    sheet.getRange("C5:C12").format.columnWidthPx = 260;
    sheet.getRange("A5:C12").format.autofitRows();
  }
  if (spec.name === "DATA_QUALITY") {
    const passColumn = normalized[0].indexOf("passed");
    if (passColumn >= 0) {
      const col = colLetter(passColumn);
      sheet.getRange(`${col}6:${col}${4 + normalized.length}`).conditionalFormats.addCustom(`=${col}6=FALSE`, { fill: red, font: { color: "#FFFFFF", bold: true } });
      sheet.getRange(`${col}6:${col}${4 + normalized.length}`).conditionalFormats.addCustom(`=${col}6=TRUE`, { fill: "#D7EBD9", font: { color: "#215A2A", bold: true } });
    }
  }
}

const modelSheet = workbook.worksheets.getItem(payload.charts.model_comparison_sheet);
const modelChart = modelSheet.charts.add("bar", modelSheet.getRange("A5:D11"));
modelChart.title = "Aynı OOS Örnekleminde Getiri ve Volatilite";
modelChart.hasLegend = true;
modelChart.setPosition("N5", "V21");

const exposureSheet = workbook.worksheets.getItem(payload.charts.exposure_sheet);
const exposureChart = exposureSheet.charts.add("bar", exposureSheet.getRange("B5:C13"));
exposureChart.title = "Dengeli Portföy Sektör Maruziyeti";
exposureChart.hasLegend = false;
exposureChart.setPosition("G5", "N21");

const costSheet = workbook.worksheets.getItem(payload.charts.cost_sheet);
const costSpec = payload.sheets.find((sheet) => sheet.name === payload.charts.cost_sheet);
const costHeaders = costSpec.rows[0];
const modelIndex = costHeaders.indexOf("model_name");
const bpsIndex = costHeaders.indexOf("transaction_cost_bps");
const sharpeIndex = costHeaders.indexOf("sharpe");
const costLevels = [5, 10, 25];
const costHelper = [["cost_bps", "Equal Weight", "GMV"], ...costLevels.map((bps) => [
  bps,
  costSpec.rows.find((row) => row[modelIndex] === "Equal Weight" && Number(row[bpsIndex]) === bps)?.[sharpeIndex] ?? "",
  costSpec.rows.find((row) => row[modelIndex] === "GMV" && Number(row[bpsIndex]) === bps)?.[sharpeIndex] ?? "",
])];
costSheet.getRange("A27:C30").values = costHelper;
costSheet.getRange("A27:C30").format = { font: { color: "#FFFFFF" }, rowHeight: 15 };
const costChart = costSheet.charts.add("line", costSheet.getRange("A27:C30"));
costChart.title = "İşlem Maliyeti Duyarlılığı";
costChart.hasLegend = true;
costChart.setPosition("L10", "T25");

const keyCheck = await workbook.inspect({
  kind: "table",
  range: "START_HERE!A1:B13",
  include: "values,formulas",
  tableMaxRows: 15,
  tableMaxCols: 3,
});
await fs.writeFile(outputPath + ".keycheck.ndjson", keyCheck.ndjson);
const errors = await workbook.inspect({
  kind: "match",
  searchTerm: "#REF!|#DIV/0!|#VALUE!|#NAME\\?|#N/A",
  options: { useRegex: true, maxResults: 300 },
  summary: "formula error scan",
});
await fs.writeFile(outputPath + ".inspect.ndjson", errors.ndjson);

const output = await SpreadsheetFile.exportXlsx(workbook);
await output.save(outputPath);
