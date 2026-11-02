CXX      ?= g++
CXXFLAGS ?= -std=c++20 -O2 -Wall -Wextra -pthread

table_sync: main.cpp bounded_queue.h harness.h coarse_service.h rw_service.h fine_service.h
	$(CXX) $(CXXFLAGS) main.cpp -o $@

doc: 
	doxygen Doxyfile

clean:
	rm -rf table_sync doc

.PHONY: doc clean
