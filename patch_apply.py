import sublime
import sublime_plugin


class PatchApplyDoCommand(sublime_plugin.TextCommand):
    def run(self, edit):
        # TDODO fetch from settings
        diff_syntax = "Packages/Diff/Diff.tmLanguage"

        new_view = sublime.active_window().new_file()
        new_view.set_syntax_file(diff_syntax)

        # self.view.`insert(edit, 0, stx)
        # s = sublime.load_settings("Patch Apply.sublime-settings")
        # first_name = s.get('first_name', 'Noname')
        # self.view.insert(edit, 0, "Hi %s!" % first_name)
