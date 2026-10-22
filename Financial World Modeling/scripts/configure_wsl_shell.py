"""Expose the existing QuantLab uv installation in new Bash sessions."""
import os
from pathlib import Path
import subprocess

START = '# >>> quant-agent-lab tools >>>'
END = '# <<< quant-agent-lab tools <<<'
BLOCK = '''# >>> quant-agent-lab tools >>>
case ":${PATH:-}:" in
    *":$HOME/.local/share/quant-lab-tools/bin:"*) ;;
    *) export PATH="$HOME/.local/share/quant-lab-tools/bin:${PATH:-}" ;;
esac
# <<< quant-agent-lab tools <<<
'''


def main():
    if os.environ.get('WSL_DISTRO_NAME') != 'QuantLab' or os.getuid() == 0:
        raise SystemExit('Run as the normal user inside QuantLab.')
    home = Path.home()
    assert (home / '.local/share/quant-lab-tools/bin/uv').is_file()
    login = next((home / name for name in ['.bash_profile', '.bash_login', '.profile']
                  if (home / name).exists()), home / '.profile')
    for path in [home / '.bashrc', login]:
        original = path.read_text() if path.exists() else ''
        content = original
        if START in content:
            before, remainder = content.split(START, 1)
            _, after = remainder.split(END, 1)
            content = before + after.lstrip('\n')
        # Before .bashrc's noninteractive return, so login-shell sourcing works.
        updated = BLOCK + content
        if updated != original:
            path.write_text(updated)
            print('Updated:', path)
        else:
            print('Already configured:', path)
    # Start from the system PATH, excluding the parent process's uv workaround.
    env = dict(os.environ, PATH='/usr/bin:/bin')
    for flag in ['-lc', '-ic']:
        process = subprocess.run(['/bin/bash', flag, 'command -v uv && uv --version'],
                                 env=env, capture_output=True, text=True)
        print(f'Fresh bash {flag}:', process.stdout.strip())
        if process.returncode:
            raise SystemExit(process.stderr or process.returncode)


if __name__ == '__main__':
    main()
