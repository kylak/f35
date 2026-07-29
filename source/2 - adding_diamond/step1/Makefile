PYTHON ?= python3

F35    = F35.txt
SR     = ST.txt
OUTPUT = F35_MES.txt

.PHONY: all verify clean check-python

all: check-python $(OUTPUT)

$(OUTPUT): convert_mes.py $(F35) $(SR)
	$(PYTHON) convert_mes.py --input $(F35) --sr $(SR) --output $(OUTPUT)

verify: $(OUTPUT)
	$(PYTHON) verify.py $(OUTPUT)

check-python:
	@command -v $(PYTHON) >/dev/null 2>&1 || { \
		echo "Error: '$(PYTHON)' not found."; \
		echo "Set PYTHON to your Python 3 interpreter:"; \
		echo "  make PYTHON=python3.13"; \
		exit 1; \
	}

clean:
	rm -f $(OUTPUT)
