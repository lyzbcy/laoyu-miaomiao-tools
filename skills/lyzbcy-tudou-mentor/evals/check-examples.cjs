// Run only the explicitly marked, self-contained examples; no company source or network.
const fs = require('node:fs');
const path = require('node:path');
const AsyncFunction = Object.getPrototypeOf(async function () {}).constructor;
const directory = path.resolve(__dirname, '../references/cases');

(async () => {
  let examples = 0;
  for (const name of fs.readdirSync(directory).filter(name => name.endsWith('.md')).sort()) {
    const markdown = fs.readFileSync(path.join(directory, name), 'utf8');
    const blocks = [...markdown.matchAll(/```js verify\r?\n([\s\S]*?)\r?\n```/g)];
    for (const block of blocks) {
      await new AsyncFunction('require', block[1])(require);
      examples++;
      process.stdout.write(`PASS ${name}\n`);
    }
  }
  if (examples !== 6) throw new Error(`Expected 6 executable examples, found ${examples}`);
  process.stdout.write('6 controlled examples passed; CSS needs browser measurement; model review evals not executed.\n');
})().catch(error => {
  process.stderr.write(`${error.stack}\n`);
  process.exitCode = 1;
});
