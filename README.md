# PWC (Paper With Code)

This tool extracts links to the implementation repositories of papers using LLM. Currently, only Usenix Security is supported.

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

## CPU implementation(prev) and GPU implementation(current)
Initially(commit:`3e613d4`), PWC was implemented using a multi-core CPU, with a highly heuristic extractor method.
The implementation has since been updated to utilize a single GPU, and the extractor now leverages an [LLM](https://huggingface.co/Qwen/Qwen2.5-1.5B-Instruct) to extract PoC code provided by the paper authors.
