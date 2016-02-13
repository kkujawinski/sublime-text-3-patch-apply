import os
import re
import sys

from functools import partial

import sublime
import sublime_plugin
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


def apply_patch(content, dir_path, strip=1, reverse=False):
    command = ['patch', '-p', str(strip), '-d', dir_path]
    if reverse:
        command.append('-R')
    p = Popen(command, stdout=PIPE, stdin=PIPE, stderr=PIPE)
    result = p.communicate(input=b(content))
    if p.returncode == 0:
        return result[0].decode('utf-8')
    else:
        output = ' '.join(command) + '\n\n'
        output += (result[0] or result[1]).decode('utf-8')
        raise PatchingFailure(output)


def prepare_exclude_pattern(excluded_dirs):
    sep = re.escape(os.path.sep)
    excluded_dirs = [re.escape(d) for d in excluded_dirs]
    return re.compile(
        '^(.*{sep})?({excluded_dirs})({sep}.*)?$'.format(
            sep=sep, excluded_dirs='|'.join(excluded_dirs)
        )
    )


class PatchApplyListener(sublime_plugin.EventListener):
    def __init__(self):
        s = sublime.load_settings('Patch Apply.sublime-settings')
        excluded_dirs = s.get('excluded_dirs', [])
        self.excluded = prepare_exclude_pattern(excluded_dirs)

    def full_process_dir_path(self, callback):
        relative_paths, full_torelative_paths = self.build_relative_paths()
        self.directory_selector(callback,
                                relative_paths, full_torelative_paths)

    def quick_process_dir_path(self, callback):
        folders = sublime.active_window().folders()
        if len(folders) == 1:
            callback(folders[0])
        else:
            relative_paths, full_torelative_paths = self.build_relative_paths(
                top_directories=True)
            self.directory_selector(callback,
                                    relative_paths, full_torelative_paths)

    def quick_process_patch_strip(self, callback):
        callback('1')

    def full_process_patch_strip(self, callback):
        sublime.active_window().show_input_panel(
            'Strip NUM leading components from file names', '1', callback,
            None, None
        )

    def on_pre_close(self, view):
        settings = view.settings()
        if not settings.get('patch_apply'):
            return

        content = view.substr(sublime.Region(0, view.size()))
        reverse_patch = bool(settings.get('reverse_apply'))
        quick_apply = settings.get('quick_apply')

        def dir_path_callback(dir_path):
            def patch_strip_callback(patch_strip):
                self.apply_patch(content, dir_path, patch_strip,
                                 reverse=reverse_patch)
            if quick_apply:
                self.quick_process_patch_strip(patch_strip_callback)
            else:
                self.full_process_patch_strip(patch_strip_callback)

        if quick_apply:
            self.quick_process_dir_path(dir_path_callback)
        else:
            self.full_process_dir_path(dir_path_callback)

    def apply_patch(self, content, dir_path, patch_strip, reverse=False):
        try:
            output = apply_patch(content, dir_path, patch_strip,
                                 reverse=reverse)
        except PatchingFailure as e:
            self.results(str(e))
        else:
            self.results(output)

    def dir_selected(self, callback, relative_paths,
                     full_torelative_paths, selected_index):
        if selected_index != -1:
            selected_dir = relative_paths[selected_index]
            selected_dir = full_torelative_paths[selected_dir]
            callback(selected_dir)

    def directory_selector(self, callback, relative_paths,
                           full_torelative_paths):
        if len(relative_paths) == 1:
            selected_dir = relative_paths[0]
            selected_dir = full_torelative_paths[selected_dir]
            callback(selected_dir)
        elif len(relative_paths) > 1:
            # self.move_current_directory_to_top()
            sublime.active_window().show_quick_panel(
                relative_paths,
                partial(self.dir_selected, callback, relative_paths,
                        full_torelative_paths)
            )

    def build_relative_paths(self, top_directories=False):
        folders = sublime.active_window().folders()
        relative_paths = []
        full_torelative_paths = {}
        for path in folders:
            rootfolders = os.path.split(path)[-1]
            rel_path_start = os.path.split(path)[0]

            full_torelative_paths[rootfolders] = path
            if not self.excluded.search(rootfolders):
                relative_paths.append(rootfolders)

            if top_directories:
                continue

            for base, dirs, files in os.walk(path):
                for dir_ in dirs:
                    relative_path = os.path.relpath(os.path.join(base, dir_),
                                                    rel_path_start)
                    local_path = os.path.join(base, dir_)
                    full_torelative_paths[relative_path] = local_path
                    if not self.excluded.search(relative_path):
                        relative_paths.append(relative_path)
        return relative_paths, full_torelative_paths

    def results(self, content):
        window = sublime.active_window()
        output = window.create_output_panel('patch_apply_results')
        output.run_command('erase_view')
        output.run_command('append', {'characters': content})
        window.run_command('show_panel',
                           {'panel': 'output.patch_apply_results'})


class PatchApplyCommand(sublime_plugin.TextCommand):
    def _get_new_view(self):
        s = sublime.load_settings('Patch Apply.sublime-settings')
        diff_syntax = s.get('diff_syntax', 'Packages/Diff/Diff.tmLanguage')
        new_view = sublime.active_window().new_file()
        new_view.set_name('Paste & apply patch')
        new_view.set_syntax_file(diff_syntax)
        new_view.set_scratch(True)
        new_view.settings().set('patch_apply', True)
        return new_view

    def run(self, edit):
        self._get_new_view()


class QuickApplyMixin(object):
    def _get_new_view(self):
        new_view = super(QuickApplyMixin, self)._get_new_view()
        new_view.settings().set('quick_apply', True)
        return new_view


class ReverseApplyMixin(object):
    def _get_new_view(self):
        new_view = super(ReverseApplyMixin, self)._get_new_view()
        new_view.settings().set('reverse_apply', True)
        return new_view


class PatchApplyReverseCommand(ReverseApplyMixin, PatchApplyCommand):
    pass


class PatchQuickApplyCommand(QuickApplyMixin, PatchApplyCommand):
    pass


class PatchQuickApplyReverseCommand(QuickApplyMixin, ReverseApplyMixin,
                                    PatchApplyCommand):
    pass
