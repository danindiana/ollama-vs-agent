.PHONY: setup scan dashboard clean test

setup:
	pip install -r requirements.txt

scan:
	cd chm_project && python3 analyzer.py .

dashboard:
	cd chm_project && python3 dashboard.py

test:
	pytest tests/

clean:
	rm -rf __pycache__ .pytest_cache 
	find . -type d -name "__pycache__" -exec rm -rf {} +
