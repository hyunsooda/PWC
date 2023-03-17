# PWC (Paper With Code)

This tool extracts links to the implementation repositories of papers. Currently, only Usenix Security is supported.

How to run:
```
./pwc --help
Usage: pwc (-c|--conference ARG) (-y|--year ARG) (-l|--cycle ARG)
            (-o|--output ARG) [-m|--maxsize ARG]

  PWC (Paper With Code)

Available options:
  -c,--conference ARG      target conference name (usenix | ccs | ndss | s&p)
  -y,--year ARG            publication year
  -l,--cycle ARG           cycle (spring | summer | fall | winter)
  -o,--output ARG          output path
  -m,--maxsize ARG         allowed pdf max size to be extracted
  -h,--help                Show this help text
```

```
./pwc -c usenix -y 2022 -l winter -o usenix-sec22-winter
```

The output will be placed in `usenix-sec22-winter/result.txt`
```
Piranha: A GPU Platform for Secure Computation --> https://github.com/ucbrise/piranha
Half-Double: Hammering From the Next Row Over --> https://github.com/iaik/halfdouble
...
```

The extractor method is highly heuristic, so it may not be able to extract implementation repository links for some papers.

# Build
```
cabal build
```
