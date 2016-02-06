import sublime
import sublime_plugin
import sys
from subprocess import Popen, PIPE


if sys.version_info < (3,):
    def b(x):
        return x
else:
    import codecs

    def b(x):
        return codecs.latin_1_encode(x)[0]


class PatchingFailure(Exception):
    pass


def apply_patch(content, dir_path, strip=1):
    p = Popen(
        ["patch", "-p", str(strip), "-d", dir_path],
        stdout=PIPE, stdin=PIPE, stderr=PIPE
    )
    result = p.communicate(input=b(content))
    if p.returncode == 0:
        return result[0].decode("utf-8")
    else:
        raise PatchingFailure(result[1].decode("utf-8"))


class PatchApplyListener(sublime_plugin.EventListener):
    def on_pre_close(self, view):
        if not view.settings().get('patch_apply'):
            return

        dir_path = sublime.active_window().extract_variables()['folder']
        content = view.substr(sublime.Region(0, view.size()))
        try:
            output = apply_patch(content, dir_path)
        except PatchingFailure as e:
            self.results(str(e))
        else:
            self.results(output)

    def results(self, content):
        window = sublime.active_window()
        output = window.create_output_panel('patch_apply_results')
        output.run_command('erase_view')
        output.run_command('append', {'characters': content})
        window.run_command('show_panel',
                           {'panel': 'output.patch_apply_results'})


class PatchApplyDoCommand(sublime_plugin.TextCommand):
    def run(self, edit):
        diff_syntax = "Packages/Diff/Diff.tmLanguage"

        new_view = sublime.active_window().new_file()
        new_view.set_name("Paste & apply patch")
        new_view.set_syntax_file(diff_syntax)
        new_view.set_scratch(True)
        new_view.settings().set('patch_apply', True)
