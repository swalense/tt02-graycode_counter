import unittest

if __name__ == "__main__":

    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    suite.addTests(loader.discover(".", pattern="*.py", top_level_dir="."))

    runner = unittest.TextTestRunner()
    runner.run(suite)
