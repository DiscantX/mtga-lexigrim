# Processing Time Breakdowns

## Raw Performance Reports
```
FE_THREADS = 4

============================== BATCH_SIZE = 1 ==============================

=== Ingestion Pipeline Performance Report ===
  - Qdrant Upsert: 103.911s total (50 calls, avg 2.0782s, 70.6%)                                                         
  - Fetch Existing Card IDs: 14.483s total (1 calls, avg 14.4833s, 9.8%)                                                 
  - Streaming & Filtering: 14.209s total (1 calls, avg 14.2086s, 9.7%)                                                   
  - FastEmbed Generation: 12.514s total (50 calls, avg 0.2503s, 8.5%)                                                    
  - Pre-scan Line Count: 1.951s total (1 calls, avg 1.9506s, 1.3%)                                                       
  - Payload Cleaning & Point Prep: 0.106s total (50 calls, avg 0.0021s, 0.1%)                                            
  - Text Formatting & Cache Lookup: 0.001s total (50 calls, avg 0.0000s, 0.0%)                                           
Total time measured: 147.174s                                                                                            

                                                                                                                         
=== Ingestion Pipeline Performance Report ===
  - Qdrant Upsert: 207.168s total (100 calls, avg 2.0717s, 79.4%)                                                        
  - FastEmbed Generation: 22.913s total (100 calls, avg 0.2291s, 8.8%)                                                   
  - Fetch Existing Card IDs: 14.483s total (1 calls, avg 14.4833s, 5.6%)                                                 
  - Streaming & Filtering: 14.209s total (1 calls, avg 14.2086s, 5.4%)                                                   
  - Pre-scan Line Count: 1.951s total (1 calls, avg 1.9506s, 0.7%)                                                       
  - Payload Cleaning & Point Prep: 0.207s total (100 calls, avg 0.0021s, 0.1%)                                           
  - Text Formatting & Cache Lookup: 0.001s total (100 calls, avg 0.0000s, 0.0%)                                          
Total time measured: 260.932s     

============================== BATCH_SIZE = 2 ==============================

=== Ingestion Pipeline Performance Report ===
  - Qdrant Upsert: 103.368s total (50 calls, avg 2.0674s, 67.3%)                                                     
  - FastEmbed Generation: 20.110s total (50 calls, avg 0.4022s, 13.1%)                                               
  - Fetch Existing Card IDs: 14.401s total (1 calls, avg 14.4013s, 9.4%)                                             
  - Streaming & Filtering: 13.412s total (1 calls, avg 13.4117s, 8.7%)                                               
  - Pre-scan Line Count: 2.114s total (1 calls, avg 2.1143s, 1.4%)                                                   
  - Payload Cleaning & Point Prep: 0.200s total (50 calls, avg 0.0040s, 0.1%)                                        
  - Text Formatting & Cache Lookup: 0.001s total (50 calls, avg 0.0000s, 0.0%)                                       
Total time measured: 153.607s                                                                                        

                                                                                                                     
=== Ingestion Pipeline Performance Report ===
  - Qdrant Upsert: 206.574s total (100 calls, avg 2.0657s, 74.8%)                                                    
  - FastEmbed Generation: 39.330s total (100 calls, avg 0.3933s, 14.2%)                                              
  - Fetch Existing Card IDs: 14.401s total (1 calls, avg 14.4013s, 5.2%)                                             
  - Streaming & Filtering: 13.412s total (1 calls, avg 13.4117s, 4.9%)                                               
  - Pre-scan Line Count: 2.114s total (1 calls, avg 2.1143s, 0.8%)                                                   
  - Payload Cleaning & Point Prep: 0.411s total (100 calls, avg 0.0041s, 0.1%)                                       
  - Text Formatting & Cache Lookup: 0.001s total (100 calls, avg 0.0000s, 0.0%)                                      
Total time measured: 276.243s  

============================== BATCH_SIZE = 4 ==============================

=== Ingestion Pipeline Performance Report ===
  - Qdrant Upsert: 103.805s total (50 calls, avg 2.0761s, 59.2%)                                                                                                               
  - FastEmbed Generation: 43.682s total (50 calls, avg 0.8736s, 24.9%)                                                                                                         
  - Streaming & Filtering: 12.934s total (1 calls, avg 12.9341s, 7.4%)                                                                                                         
  - Fetch Existing Card IDs: 12.324s total (1 calls, avg 12.3236s, 7.0%)                                                                                                       
  - Pre-scan Line Count: 2.357s total (1 calls, avg 2.3566s, 1.3%)                                                                                                             
  - Payload Cleaning & Point Prep: 0.386s total (50 calls, avg 0.0077s, 0.2%)                                                                                                  
  - Text Formatting & Cache Lookup: 0.001s total (50 calls, avg 0.0000s, 0.0%)                                                                                                 
Total time measured: 175.488s

=== Ingestion Pipeline Performance Report ===
  - Qdrant Upsert: 207.204s total (100 calls, avg 2.0720s, 63.9%)                                                                                                              
  - FastEmbed Generation: 88.611s total (100 calls, avg 0.8861s, 27.3%)                                                                                                        
  - Streaming & Filtering: 12.934s total (1 calls, avg 12.9341s, 4.0%)                                                                                                         
  - Fetch Existing Card IDs: 12.324s total (1 calls, avg 12.3236s, 3.8%)                                                                                                       
  - Pre-scan Line Count: 2.357s total (1 calls, avg 2.3566s, 0.7%)                                                                                                             
  - Payload Cleaning & Point Prep: 0.778s total (100 calls, avg 0.0078s, 0.2%)                                                                                                 
  - Text Formatting & Cache Lookup: 0.002s total (100 calls, avg 0.0000s, 0.0%)                                                                                                
Total time measured: 324.209s        

============================== BATCH_SIZE = 8 ==============================

=== Ingestion Pipeline Performance Report ===
  - FastEmbed Generation: 110.258s total (50 calls, avg 2.2052s, 40.5%)                                                                                                        
  - Qdrant Upsert: 104.414s total (50 calls, avg 2.0883s, 38.4%)                                                                                                               
  - Streaming & Filtering: 46.308s total (1 calls, avg 46.3076s, 17.0%)                                                                                                        
  - Fetch Existing Card IDs: 8.281s total (1 calls, avg 8.2812s, 3.0%)                                                                                                         
  - Pre-scan Line Count: 1.912s total (1 calls, avg 1.9117s, 0.7%)                                                                                                             
  - Payload Cleaning & Point Prep: 0.867s total (50 calls, avg 0.0173s, 0.3%)                                                                                                  
  - Text Formatting & Cache Lookup: 0.008s total (50 calls, avg 0.0002s, 0.0%)                                                                                                 
Total time measured: 272.048s                                                                                                                                                  
                                                                                                                                                                               
=== Ingestion Pipeline Performance Report ===
  - Qdrant Upsert: 208.637s total (100 calls, avg 2.0864s, 44.4%)                                                                                                              
  - FastEmbed Generation: 202.722s total (100 calls, avg 2.0272s, 43.2%)                                                                                                       
  - Streaming & Filtering: 46.308s total (1 calls, avg 46.3076s, 9.9%)                                                                                                         
  - Fetch Existing Card IDs: 8.281s total (1 calls, avg 8.2812s, 1.8%)                                                                                                         
  - Pre-scan Line Count: 1.912s total (1 calls, avg 1.9117s, 0.4%)                                                                                                             
  - Payload Cleaning & Point Prep: 1.701s total (100 calls, avg 0.0170s, 0.4%)                                                                                                 
  - Text Formatting & Cache Lookup: 0.017s total (100 calls, avg 0.0002s, 0.0%)                                                                                                
Total time measured: 469.578s                                                                                                                                                  


============================== BATCH_SIZE = 16 ==============================

=== Ingestion Pipeline Performance Report ===
  - FastEmbed Generation: 194.150s total (50 calls, avg 3.8830s, 59.9%)                                                                                                        
  - Qdrant Upsert: 104.422s total (50 calls, avg 2.0884s, 32.2%)                                                                                                               
  - Streaming & Filtering: 13.506s total (1 calls, avg 13.5063s, 4.2%)                                                                                                         
  - Fetch Existing Card IDs: 8.240s total (1 calls, avg 8.2400s, 2.5%)                                                                                                         
  - Pre-scan Line Count: 2.308s total (1 calls, avg 2.3081s, 0.7%)                                                                                                             
  - Payload Cleaning & Point Prep: 1.518s total (50 calls, avg 0.0304s, 0.5%)                                                                                                  
  - Text Formatting & Cache Lookup: 0.005s total (50 calls, avg 0.0001s, 0.0%)

 === Ingestion Pipeline Performance Report ===
  - FastEmbed Generation: 386.209s total (100 calls, avg 3.8621s, 62.1%)                                                                                                       
  - Qdrant Upsert: 208.854s total (100 calls, avg 2.0885s, 33.6%)                                                                                                              
  - Streaming & Filtering: 13.506s total (1 calls, avg 13.5063s, 2.2%)                                                                                                         
  - Fetch Existing Card IDs: 8.240s total (1 calls, avg 8.2400s, 1.3%)                                                                                                         
  - Payload Cleaning & Point Prep: 3.096s total (100 calls, avg 0.0310s, 0.5%)                                                                                                 
  - Pre-scan Line Count: 2.308s total (1 calls, avg 2.3081s, 0.4%)                                                                                                             
  - Text Formatting & Cache Lookup: 0.009s total (100 calls, avg 0.0001s, 0.0%)                                                                                                
Total time measured: 622.223s

============================== BATCH_SIZE = 32 ==============================

=== Ingestion Pipeline Performance Report ===
  - FastEmbed Generation: 527.434s total (50 calls, avg 10.5487s, 78.2%)                                                                          
  - Qdrant Upsert: 111.882s total (50 calls, avg 2.2376s, 16.6%)                                                                                  
  - Fetch Existing Card IDs: 14.357s total (1 calls, avg 14.3567s, 2.1%)                                                                          
  - Streaming & Filtering: 14.351s total (1 calls, avg 14.3510s, 2.1%)                                                                            
  - Payload Cleaning & Point Prep: 3.198s total (50 calls, avg 0.0640s, 0.5%)                                                                     
  - Pre-scan Line Count: 2.952s total (1 calls, avg 2.9518s, 0.4%)                                                                                
  - Text Formatting & Cache Lookup: 0.073s total (50 calls, avg 0.0015s, 0.0%)                                                                    
Total time measured: 674.246s   
                                                                                                                                   
=== Ingestion Pipeline Performance Report ===
  - FastEmbed Generation: 960.043s total (100 calls, avg 9.6004s, 78.8%)                                                                          
  - Qdrant Upsert: 220.816s total (100 calls, avg 2.2082s, 18.1%)                                                                                 
  - Fetch Existing Card IDs: 14.357s total (1 calls, avg 14.3567s, 1.2%)                                                                          
  - Streaming & Filtering: 14.351s total (1 calls, avg 14.3510s, 1.2%)                                                                            
  - Payload Cleaning & Point Prep: 6.083s total (100 calls, avg 0.0608s, 0.5%)                                                                    
  - Pre-scan Line Count: 2.952s total (1 calls, avg 2.9518s, 0.2%)                                                                                
  - Text Formatting & Cache Lookup: 0.249s total (100 calls, avg 0.0025s, 0.0%)                                                                   
Total time measured: 1218.852s
```    



## Breakdowns

### Pipeline Component Breakdown (%)

| Batch Size | Total Items | FastEmbed Total | Qdrant Total | Total Time | FE % | Qdrant % | Throughput |
| --- | --- | --- | --- | --- | --- | --- | --- |
| **1** | 100 | **22.91s** | 207.17s | 260.93s | 8.8% | **79.4%** | 0.38 items/s |
| **2** | 200 | **39.33s** | 206.57s | 276.24s | 14.2% | **74.8%** | 0.72 items/s |
| **4** | 400 | **88.61s** | 207.20s | 324.21s | 27.3% | **63.9%** | 1.23 items/s |
| **8** | 800 | **202.72s** | 208.64s | 469.58s | 43.2% | **44.4%** | 1.70 items/s |
| **16** | 1,600 | **386.21s** | 208.85s | 622.22s | **62.1%** | 33.6% | 2.57 items/s |
| **32** | 3,200 | **960.04s** | 220.82s | 1,218.85s | **78.8%** | 18.1% | 2.63 items/s |

#### Core Insights From Component Breakdown

1.  **The Qdrant Floor:**  
    No matter how many items you send, Qdrant takes **~207 to 220 seconds** across 100 calls. The database cost is entirely sequential network latency (roughly ~2.08 seconds per round-trip). It does not care about your batch size; it only cares about the number of calls. 
2.  **The Inversion Point (Batch Size 8):**  
    At **Batch Size 8**, the pipeline reaches a perfect equilibrium where local embedding creation (~202s) takes almost the exact same amount of time as the remote database upsert (~208s). 
3.  **The Efficiency Collapse (Batch Size 32):**  
    Look at the explosion of FastEmbed time between 16 and 32. It more than **doubles** (**386s → 960s**), consuming nearly 80% of the entire pipeline runtime. Your local machine is throttling hard at 32, which completely wipes out any efficiency gained from bypassing the Qdrant network overhead.

### Component Throughput Breakdown (Items/Second)

| Batch Size | Total Items | FastEmbed Throughput | Qdrant Throughput | Overall System Throughput |
| --- | --- | --- | --- | --- |
| **1** | 100 | 4.36 items/s | 0.48 items/s | **0.38 items/s** |
| **2** | 200 | 5.09 items/s | 0.97 items/s | **0.72 items/s** |
| **4** | 400 | 4.51 items/s | 1.93 items/s | **1.23 items/s** |
| **8** | 800 | 3.95 items/s | 3.83 items/s | **1.70 items/s** |
| **16** | 1,600 | 4.14 items/s | 7.66 items/s | **2.57 items/s** |
| **32** | 3,200 | **3.33 items/s** | **14.49 items/s** | **2.63 items/s** |

#### Key Takeaways from Component Speeds

1.  **The Qdrant Scaling Illusion:**  
    Look at Qdrant’s standalone throughput. It scales beautifully and nearly linearly (**0.48 → 14.49 items/s**) because it loves larger batches. It easily handles 32 items in the same 2-second network window it takes to handle 1 item. 
2.  **The FastEmbed Speed Cap:**  
    Your CPU's sweet spot for generation is **Batch Size 2**, where it peaks at **5.09 items/s**. Once you push the batch size past 16, local generation performance degrades significantly, dropping down to **3.33 items/s** at Batch Size 32. 
3.  **The Pipeline Drag:**  
    Because the current script is strictly sequential, the overall system throughput is always throttled by the _slowest_ component in the loop.