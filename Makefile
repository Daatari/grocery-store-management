CXX = clang++
CXXFLAGS = -std=c++17 -Wall

SRC_DIR=src
SRCS = $(wildcard $(SRC_DIR)/*.cpp)
TARGET = build/main

all: build $(TARGET)

build:
	mkdir -p build

$(TARGET): $(SRCS)
	$(CXX) $(CXXFLAGS) $(SRCS) -o $(TARGET)

clean:
	rm -rf build