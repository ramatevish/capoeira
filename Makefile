all:
	make test
	make style

clean:
	find . -type f -name "*.py[co]" -exec rm -v {} \;

style:
	pep8 --ignore=E501 --repeat --show-source .
	importchecker ./