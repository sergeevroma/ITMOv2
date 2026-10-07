/**
 * OpenCode plugin: check-after-edit
 *
 * Запускает sh scripts/check.sh из каталога room_booking_project текущего worktree
 * после изменений Python-файлов инструментами агента (edit/write/apply_patch).
 * Выполняет проверки последовательно, с тайм-аутом 30 секунд.
 * Добавляет PASS/FAIL, код завершения и вывод проверки в output.output результата инструмента.
 */

/** @type {import('@opencode-ai/plugin').Plugin} */
export default async ({ directory }) => {
  const isPython = (p) => typeof p === 'string' && p.endsWith('.py');

  function touchedPyByApplyPatch(args) {
    const text = args?.patchText;
    if (typeof text !== 'string') return false;
    // Ищем заголовки файлов из apply_patch: *** Update File: path, *** Add File: path, *** Move to: path
    const lines = text.split('\n');
    for (const line of lines) {
      if (line.startsWith('*** ')) {
        const idx = line.indexOf(':');
        if (idx !== -1) {
          const path = line.slice(idx + 1).trim();
          if (isPython(path)) return true;
        }
      }
    }
    return false;
  }

  function touchedPyByArgs(args) {
    if (!args || typeof args !== 'object') return false;
    const candidates = [];
    for (const key of ['filePath', 'path', 'to', 'from']) {
      if (isPython(args[key])) candidates.push(args[key]);
    }
    if (Array.isArray(args.files)) {
      for (const f of args.files) {
        if (isPython(f)) candidates.push(f);
      }
    }
    return candidates.length > 0;
  }

  async function runChecks(cwd) {
    const { execFile } = await import('node:child_process');
    const { join } = await import('node:path');
    const workdir = join(cwd, 'room_booking_project');
    const start = Date.now();
    const cmd = 'sh';
    const args = ['scripts/check.sh'];
    const timeoutMs = 30_000;
    return new Promise((resolve) => {
      const child = execFile(
        cmd,
        args,
        { cwd: workdir, timeout: timeoutMs, maxBuffer: 10 * 1024 * 1024 },
        (err, stdout, stderr) => {
          const duration = Date.now() - start;
          const code = err && typeof err.code === 'number' ? err.code : 0;
          const ok = !err;
          resolve({ ok, code, stdout: stdout ?? '', stderr: stderr ?? '', duration });
        }
      );
      // nothing else; rely on callback
    });
  }

  return {
    async 'tool.execute.after'(input, output) {
      const name = input?.tool?.name || input?.tool || '';
      const args = input?.args;
      const isEditLike = ['edit', 'write', 'apply_patch'].includes(String(name));
      if (!isEditLike) return;

      // Определяем, затронуты ли Python-файлы
      let touchesPy = false;
      if (name === 'apply_patch') touchesPy = touchedPyByApplyPatch(args);
      if (!touchesPy) touchesPy = touchedPyByArgs(args);
      if (!touchesPy) return;

      const res = await runChecks(directory);
      const summary = res.ok ? 'PASS' : 'FAIL';
      const report = [
        `check-after-edit: ${summary} (code ${res.code})`,
        `duration_ms: ${res.duration}`,
        '--- stdout ---',
        res.stdout.trim(),
        '--- stderr ---',
        res.stderr.trim(),
        '---------------',
      ]
        .filter(Boolean)
        .join('\n');

      // Добавляем отчёт в стандартный вывод инструмента, чтобы агент гарантированно увидел
      if (typeof output.output === 'string') {
        output.output += `\n${report}\n`;
      } else {
        output.output = report;
      }
    },
  };
};
