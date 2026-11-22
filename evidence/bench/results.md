| Dataset | Nodes | Edges | Method | Modularity | NMI | ARI | Runtime (s) | Peak memory (MB) |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| LFR mu=0.1 | 1,000 | 8,847 | Leiden | 0.787 ± 0.000 | 1.000 ± 0.000 | 1.000 ± 0.000 | 0.0877 ± 0.0214 | 81.6 ± 0.6 |
| LFR mu=0.1 | 1,000 | 8,847 | Louvain | 0.787 ± 0.000 | 1.000 ± 0.000 | 1.000 ± 0.000 | 0.0049 ± 0.0010 | 81.8 ± 0.1 |
| LFR mu=0.3 | 1,000 | 9,196 | Leiden | 0.483 ± 0.005 | 0.978 ± 0.009 | 0.949 ± 0.056 | 0.1330 ± 0.0292 | 81.8 ± 0.1 |
| LFR mu=0.3 | 1,000 | 9,196 | Louvain | 0.485 ± 0.000 | 0.978 ± 0.005 | 0.963 ± 0.016 | 0.0080 ± 0.0011 | 81.7 ± 0.1 |
| LFR mu=0.5 | 1,000 | 9,472 | Leiden | 0.261 ± 0.003 | 0.383 ± 0.037 | 0.257 ± 0.044 | 0.7406 ± 0.1452 | 81.9 ± 0.1 |
| LFR mu=0.5 | 1,000 | 9,472 | Louvain | 0.249 ± 0.007 | 0.329 ± 0.027 | 0.177 ± 0.026 | 0.0197 ± 0.0062 | 81.7 ± 0.1 |
| email-Eu-core | 1,005 | 16,064 | Leiden | 0.416 ± 0.001 | 0.581 ± 0.017 | 0.320 ± 0.042 | 0.2461 ± 0.0679 | 82.1 ± 0.1 |
| email-Eu-core | 1,005 | 16,064 | Louvain | 0.414 ± 0.003 | 0.579 ± 0.019 | 0.315 ± 0.032 | 0.0139 ± 0.0030 | 82.0 ± 0.2 |

Mean ± standard deviation over 5 detector seed(s). Runtime covers the detection call only. Peak memory is the child process's peak resident set size after loading the graph and running detection.
