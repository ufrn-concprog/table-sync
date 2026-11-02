CXX      ?= g++
CXXFLAGS ?= -std=c++20 -O2 -Wall -Wextra -pthread

table_sync: main.cpp harness.h coarse_service.h rw_service.h fine_service.h
	$(CXX) $(CXXFLAGS) main.cpp -o $@

clean:
	rm -f table_sync

.PHONY: clean
