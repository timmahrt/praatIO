
These are development notes for myself

## Documentation

Documentation is generated with the following command:
`pdoc praatio -d google -o docs`

A live version can be seen with
`pdoc praatio -d google`

pdoc will read from praatio, as installed on the computer, so you may need to run `pip install .` if you want to generate documentation from a locally edited version of praatio.

## Tests

Tests are run with

`pytest --cov=praatio tests/`

## Release

Releases are built and deployed with:

```bash
pip install --upgrade build
python -m build
pip install --upgrade twine
twine upload dist/*
```

Don't forget to tag the release.

After releasing to pypi conda-forge should open a PR after some time (30min - 2 hours).
https://conda-forge.org/docs/maintainer/updating_pkgs.html#pushing-to-regro-cf-autotick-bot-branch

You'll need to approve the PR for it to build the release:
https://github.com/conda-forge/praatio-feedstock/pulls
