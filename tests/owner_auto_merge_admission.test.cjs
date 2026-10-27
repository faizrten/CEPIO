/* Offline, credential-free acceptance tests for the trusted auto-merge admission. */
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');

const workflow = fs.readFileSync(
  path.join(__dirname, '..', '.github', 'workflows', 'owner-auto-merge.yml'), 'utf8'
);
const marker = '          script: |\n';
assert.equal(workflow.split(marker).length, 2, 'Expected exactly one trusted workflow script');
assert.match(workflow, /workflow_run:/);
assert.match(workflow, /pull-requests: write/);
assert.doesNotMatch(workflow, /actions\/checkout@|id-token: write|contents: write/);
assert.doesNotMatch(workflow, /mergePullRequest\s*\(/);
const script = workflow.split(marker)[1].split('\n')
  .map(line => line.startsWith('            ') ? line.slice(12) : line).join('\n');
const run = new Function('context', 'github', 'core', 'return (async () => {\n' + script + '\n})();');

const SHA = 'a'.repeat(40);
const MARKER = '- [x] **PUBLIC** — public content reviewed.';
const PUBLIC_ASSURANCE = [
  '- [x] No customer-confidential data, procedures or models.',
  '- [x] No protected benchmark/evaluation corpus or proprietary industrial reasoning.',
  '- [x] I considered whether the same ecosystem value could be achieved with a narrower interface.',
  '- [x] Publication value exceeds replication/IP-exposure risk.',
].join('\n');
const low = '## Summary\nA safe guide improvement with sufficient detail.\n\n## Risk classification\n- [x] low\n\n## IP / publication review\n' + MARKER;
const med = '## Risk classification\n- [x] medium\n\n## Review automation\n- [x] R1 auto-merge authorized by founder\n\n## IP / publication review\n' + MARKER + '\n' + PUBLIC_ASSURANCE;

async function caseRun(changes = {}) {
  const file = {filename:'docs/wiki/18-Glossary.md',status:'modified',additions:3,deletions:1,patch:'@@ -1 +1 @@'};
  const pr = {
    number:12, state:'open', draft:false, merged:false, node_id:'PR_NODE_ID',
    user:{login:'faizrten'}, head:{sha:SHA,repo:{full_name:'faizrten/CEPIO'}},
    base:{ref:'main',repo:{full_name:'faizrten/CEPIO'}}, body:low,
    requested_reviewers:[],requested_teams:[],
    ...(changes.pr || {}),
  };
  let mutationCount = 0;
  let getCount = 0;
  const github = {
    rest:{pulls:{
      get:async()=>{getCount++; return {data: getCount===2 && changes.fresh ? {...pr,...changes.fresh}:pr};},
      listFiles:async()=>{},
    }},
    paginate:async()=>changes.files || [file],
    graphql:async(query)=>{assert.match(query,/enablePullRequestAutoMerge/); mutationCount++; return {};},
  };
  const logs=[];
  const core={
    notice:s=>logs.push(s),warning:s=>logs.push(s),
    summary:{addHeading:()=>core.summary,addRaw:()=>core.summary,write:async()=>{}},
  };
  const context={repo:{owner:'faizrten',repo:'CEPIO'},payload:{workflow_run:{
    event:'pull_request',conclusion:'success',head_sha: changes.runSha || SHA,
    pull_requests:changes.associations === undefined ? [{number:12}]:changes.associations,
  }}};
  await run(context,github,core);
  return {mutationCount,logs};
}

(async()=>{
  assert.equal((await caseRun()).mutationCount,1,'R0 glossary change should admit');
  assert.equal((await caseRun({files:[{filename:'docs/adr/ADR-999.md',status:'modified',additions:1,deletions:1,patch:'x'}]})).mutationCount,0);
  assert.equal((await caseRun({pr:{user:{login:'contributor'}}})).mutationCount,0);
  assert.equal((await caseRun({pr:{head:{sha:SHA,repo:{full_name:'contributor/CEPIO'}}}})).mutationCount,0);
  assert.equal((await caseRun({pr:{body:low.replace(MARKER,'- [x] **CUSTOMER CONFIDENTIAL**')}})).mutationCount,0);
  assert.equal((await caseRun({runSha:'b'.repeat(40)})).mutationCount,0);
  assert.equal((await caseRun({pr:{draft:true}})).mutationCount,0);
  assert.equal((await caseRun({files:[{filename:'.github/workflows/ci.yml',status:'modified',additions:5,deletions:0,patch:'x'}]})).mutationCount,0);
  assert.equal((await caseRun({files:[{filename:'docs/wiki/18-Glossary.md',status:'renamed',previous_filename:'docs/evil.md',additions:1,deletions:1,patch:'x'}]})).mutationCount,0);
  assert.equal((await caseRun({files:[{filename:'docs/wiki/18-Glossary.md',status:'modified',additions:1,deletions:0}]})).mutationCount,0);
  assert.equal((await caseRun({fresh:{head:{sha:'b'.repeat(40),repo:{full_name:'faizrten/CEPIO'}}}})).mutationCount,0);
  assert.equal((await caseRun({associations:[]})).mutationCount,0);
  const file={filename:'tests/test_new_synthetic_example.py',status:'added',additions:10,deletions:0,patch:'new'};
  assert.equal((await caseRun({pr:{body:med},files:[file]})).mutationCount,1,'Owner-opted additive R1 test should admit');
  assert.equal((await caseRun({pr:{body:med.replace('- [x] R1 auto-merge authorized by founder','- [ ] R1 auto-merge authorized by founder')},files:[file]})).mutationCount,0);
  assert.equal((await caseRun({pr:{body:med},files:[{...file,status:'modified'}]})).mutationCount,0);
  assert.equal((await caseRun({pr:{body:med},files:[{...file,filename:'tests/test_security_regression.py'}]})).mutationCount,0);
  console.log('PASS: 16 founder-only automation cases, including R0/R1 admission and R2/R3 denials');
})().catch(err=>{console.error(err);process.exitCode=1;});
