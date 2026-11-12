"""Test CLI routing and real kernel cleanup without running research training."""
from contextlib import redirect_stderr
import io
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

import nbformat
from nbclient.exceptions import CellExecutionError
import jupyter_client
import run_project


class RunnerTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.root_patch = patch.object(run_project, 'ROOT', self.root)
        self.data_patch = patch.object(run_project, 'DATA', self.root / 'data' / '20news_preprocessed.npz')
        self.root_patch.start()
        self.data_patch.start()

    def tearDown(self):
        self.data_patch.stop()
        self.root_patch.stop()
        self.temporary.cleanup()

    def test_all_orders_preparation_seven_experiments_then_report(self):
        def finish_preprocessing(source, destination, timeout):
            if source.name == 'preprocessing.ipynb':
                run_project.DATA.parent.mkdir(parents=True)
                run_project.DATA.touch()
        with patch.object(run_project, 'run_notebook', side_effect=finish_preprocessing) as execute:
            self.assertEqual(run_project.main(['all']), 0)
        sources = [call.args[0].name for call in execute.call_args_list]
        self.assertEqual(sources, ['preprocessing.ipynb', *run_project.EXPERIMENTS.values(), 'Result.ipynb'])
        self.assertTrue((self.root / 'executed_notebooks' / 'last_run_environment.json').is_file())

    def test_selected_experiments_require_data_and_keep_requested_order(self):
        with redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
            run_project.main(['experiments', '--only', '04'])
        run_project.DATA.parent.mkdir()
        run_project.DATA.touch()
        with patch.object(run_project, 'run_notebook') as execute:
            run_project.main(['experiments', '--only', '04', '01', '04'])
        self.assertEqual([call.args[0].name for call in execute.call_args_list],
                         [run_project.EXPERIMENTS['04'], run_project.EXPERIMENTS['01']])

    def test_kernel_uses_active_python_and_closes_on_success_and_failure(self):
        original_manager = jupyter_client.KernelManager
        managers = []

        def make_manager(*args, **kwargs):
            manager = original_manager(*args, **kwargs)
            managers.append(manager)
            return manager

        source = self.root / 'check.ipynb'
        destination = self.root / 'executed_notebooks' / 'check.ipynb'
        nbformat.write(nbformat.v4.new_notebook(cells=[nbformat.v4.new_code_cell(
            f'import sys\nassert sys.executable == {sys.executable!r}\nprint("runner verified")'
        )]), source)
        with patch('jupyter_client.KernelManager', make_manager):
            run_project.run_notebook(source, destination, 30)
        saved = nbformat.read(destination, as_version=4)
        self.assertIn('runner verified', saved.cells[0].outputs[0].text)
        self.assertFalse(managers[-1].has_kernel)
        nbformat.write(nbformat.v4.new_notebook(cells=[nbformat.v4.new_code_cell(
            'raise ValueError("intentional test failure")'
        )]), source)
        with patch('jupyter_client.KernelManager', make_manager), redirect_stderr(io.StringIO()):
            with self.assertRaises(CellExecutionError):
                run_project.run_notebook(source, destination, 30)
        self.assertFalse(managers[-1].has_kernel)
        self.assertTrue((self.root / 'executed_notebooks' / 'check.failed.ipynb').exists())


if __name__ == '__main__':
    unittest.main()
