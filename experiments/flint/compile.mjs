/** Synthetic read-only Flint compiler probe; no network, MCP or external data calls. */
import { readFileSync, readdirSync, mkdirSync, writeFileSync } from 'node:fs';
import { basename, join } from 'node:path';
import { assembleVegaLite } from 'flint-chart';
import { validateChart } from 'flint-chart/validate';

const [inputDir, outputDir] = process.argv.slice(2);
if (!inputDir || !outputDir) {
  throw new Error('usage: node compile.mjs <synthetic-envelope-dir> <chart-spec-output-dir>');
}
mkdirSync(outputDir, { recursive: true });
const inputs = readdirSync(inputDir).filter((name) => name.endsWith('.json')).sort();
if (inputs.length !== 3) throw new Error('expected exactly three synthetic CEPIO chart envelopes');

for (const name of inputs) {
  const envelope = JSON.parse(readFileSync(join(inputDir, name), 'utf8'));
  if (envelope.contract_version !== 'cepio.visualization/0.1' ||
      envelope.qualification !== 'SYNTHETIC_DEVELOPMENT_ONLY' ||
      envelope.tenant_id !== 'offline-synthetic') {
    throw new Error('unqualified or out-of-scope visualization envelope');
  }
  const input = envelope.flint_input;
  if (!input || !Array.isArray(input.data?.values) || 'url' in input.data ||
      input.data.values.length !== 8) {
    throw new Error('only the authorized eight-row inline synthetic fixture is accepted');
  }
  if (!input.interaction_spec?.interactions?.length) {
    throw new Error('interactive chart intent is missing');
  }
  const validated = validateChart(input, 'vegalite', {
    maxDataRows: 500,
    maxCanvasDim: 1200,
  });
  if (!validated.valid) {
    throw new Error('Flint rejected the semantic chart input: ' + JSON.stringify(validated.errors));
  }
  const compiled = assembleVegaLite(input);
  if (!compiled || typeof compiled !== 'object') {
    throw new Error('Flint compiler failed to produce a Vega-Lite spec');
  }
  // Upstream may change output JSON format; CEPIO only owns its source input contract.
  const report = {
    source: 'cepio.visualization/0.1',
    compiler: 'flint-chart@1.0.1',
    case_id: envelope.case_id,
    signal_id: envelope.signal_id,
    data_sha256: envelope.data_sha256,
    provenance_sha256: envelope.provenance_sha256,
    row_count: input.data.values.length,
    interaction_intent: input.interaction_spec,
    validation_warnings: validated.warnings ?? [],
    spec: compiled,
  };
  writeFileSync(
    join(outputDir, basename(name, '.json') + '.vegalite.json'),
    JSON.stringify(report, null, 2) + '\n',
    'utf8',
  );
  console.log('FLINT_COMPILE_OK ' + envelope.signal_id + ' rows=' + report.row_count);
}
