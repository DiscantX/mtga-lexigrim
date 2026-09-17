# FastEmbed Thread Tuning Grid Search
Generated on: 2026-09-16 02:37:50
Configuration: 50 calls per permutation, Model: nomic-ai/nomic-embed-text-v1.5

### Leaderboard (Fastest to Slowest)
| Rank | FE_THREADS | BATCH_SIZE | Total Time (s) | Throughput (Items/s) |
| :---: | :---: | :---: | :---: | :---: |
| 1 | 2 | 2 | 7.456s | **13.41 items/s** |
| 2 | 4 | 2 | 7.494s | **13.34 items/s** |
| 3 | 2 | 4 | 16.356s | **12.23 items/s** |
| 4 | 4 | 4 | 16.471s | **12.14 items/s** |
| 5 | 4 | 1 | 4.252s | **11.76 items/s** |
| 6 | 4 | 8 | 36.700s | **10.90 items/s** |
| 7 | 2 | 8 | 37.942s | **10.54 items/s** |
| 8 | 2 | 1 | 4.978s | **10.05 items/s** |
| 9 | 1 | 2 | 11.762s | **8.50 items/s** |
| 10 | 1 | 1 | 6.938s | **7.21 items/s** |
| 11 | 1 | 4 | 30.190s | **6.62 items/s** |
| 12 | 1 | 8 | 62.691s | **6.38 items/s** |
| 13 | 4 | 16 | 156.962s | **5.10 items/s** |
| 14 | 2 | 16 | 175.645s | **4.55 items/s** |
| 15 | 6 | 2 | 23.942s | **4.18 items/s** |
| 16 | 6 | 8 | 106.443s | **3.76 items/s** |
| 17 | 6 | 4 | 54.288s | **3.68 items/s** |
| 18 | 6 | 1 | 14.205s | **3.52 items/s** |
| 19 | 1 | 16 | 285.340s | **2.80 items/s** |
| 20 | 6 | 16 | 300.106s | **2.67 items/s** |
| 21 | 8 | 2 | 39.209s | **2.55 items/s** |
| 22 | 8 | 8 | 168.353s | **2.38 items/s** |
| 23 | 8 | 4 | 84.881s | **2.36 items/s** |
| 24 | 8 | 1 | 22.080s | **2.26 items/s** |
| 25 | 8 | 16 | 424.744s | **1.88 items/s** |

### Current Optimal Configuration
* **FE_THREADS**: 2
* **BATCH_SIZE**: 2
* **Peak Throughput**: 13.41 items/s