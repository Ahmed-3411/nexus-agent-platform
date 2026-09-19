import type { BenchmarkResult } from "@/lib/types";

export const stackResults: BenchmarkResult[] = [
  {mode:"stack",scenario:"denied_path",concurrency:1,n:500,success_rate:1,mean_ms:3.8729595,p50_ms:3.6998805,p95_ms:4.75380625,p99_ms:6.30765279,throughput_ops_s:256.2543153},
  {mode:"stack",scenario:"denied_path",concurrency:5,n:500,success_rate:1,mean_ms:14.183483,p50_ms:13.952834,p95_ms:17.5373112,p99_ms:22.218619,throughput_ops_s:332.2025316},
  {mode:"stack",scenario:"denied_path",concurrency:10,n:500,success_rate:1,mean_ms:25.6426525,p50_ms:24.684158,p95_ms:31.3655091,p99_ms:95.8499262,throughput_ops_s:353.840417},
  {mode:"stack",scenario:"denied_path",concurrency:25,n:500,success_rate:1,mean_ms:75.0823614,p50_ms:66.1356675,p95_ms:167.474704,p99_ms:177.6825159,throughput_ops_s:303.4473703},
  {mode:"stack",scenario:"read_path",concurrency:1,n:500,success_rate:1,mean_ms:6.3432708,p50_ms:5.89903,p95_ms:8.1457936,p99_ms:10.0713467,throughput_ops_s:110.1465247},
  {mode:"stack",scenario:"read_path",concurrency:5,n:500,success_rate:1,mean_ms:26.7938873,p50_ms:24.992971,p95_ms:35.1427396,p99_ms:99.3914378,throughput_ops_s:177.6350463},
  {mode:"stack",scenario:"read_path",concurrency:10,n:500,success_rate:1,mean_ms:47.4851577,p50_ms:44.587285,p95_ms:64.3800321,p99_ms:132.7607417,throughput_ops_s:199.1195244},
  {mode:"stack",scenario:"read_path",concurrency:25,n:500,success_rate:1,mean_ms:123.166382,p50_ms:111.712166,p95_ms:222.1306856,p99_ms:239.269864,throughput_ops_s:192.5201434},
  {mode:"stack",scenario:"approval_path",concurrency:1,n:500,success_rate:1,mean_ms:8.3758222,p50_ms:7.9330765,p95_ms:11.0244006,p99_ms:14.3883535,throughput_ops_s:118.9362467},
  {mode:"stack",scenario:"approval_path",concurrency:5,n:500,success_rate:1,mean_ms:35.4224064,p50_ms:34.0691265,p95_ms:44.2346158,p99_ms:57.5744782,throughput_ops_s:137.8254318},
  {mode:"stack",scenario:"approval_path",concurrency:10,n:500,success_rate:1,mean_ms:66.5387273,p50_ms:62.6321275,p95_ms:80.497438,p99_ms:172.1447729,throughput_ops_s:146.0256621},
  {mode:"stack",scenario:"approval_path",concurrency:25,n:500,success_rate:1,mean_ms:172.3392771,p50_ms:160.4683385,p95_ms:300.2198237,p99_ms:338.0003763,throughput_ops_s:140.4220216},
];

export const syntheticResults: BenchmarkResult[] = [
  {mode:"synthetic",scenario:"denied_path",concurrency:1,n:500,success_rate:1,mean_ms:3.3026477,p50_ms:3.27608,p95_ms:3.4437521,p99_ms:3.7063057,throughput_ops_s:300.458659},
  {mode:"synthetic",scenario:"denied_path",concurrency:5,n:500,success_rate:1,mean_ms:3.3488771,p50_ms:3.3107905,p95_ms:3.5473692,p99_ms:3.65084,throughput_ops_s:1459.0577014},
  {mode:"synthetic",scenario:"denied_path",concurrency:10,n:500,success_rate:1,mean_ms:3.4868538,p50_ms:3.4336685,p95_ms:3.6103604,p99_ms:5.4406082,throughput_ops_s:2766.6439112},
  {mode:"synthetic",scenario:"denied_path",concurrency:25,n:500,success_rate:1,mean_ms:3.7456751,p50_ms:3.76493,p95_ms:4.1016861,p99_ms:4.3593391,throughput_ops_s:6153.2858072},
  {mode:"synthetic",scenario:"read_path",concurrency:1,n:500,success_rate:1,mean_ms:23.8867125,p50_ms:23.84946,p95_ms:24.1615425,p99_ms:24.9284489,throughput_ops_s:41.7736675},
  {mode:"synthetic",scenario:"read_path",concurrency:5,n:500,success_rate:1,mean_ms:24.0000151,p50_ms:23.958938,p95_ms:24.2509581,p99_ms:24.9825013,throughput_ops_s:207.4027075},
  {mode:"synthetic",scenario:"read_path",concurrency:10,n:500,success_rate:1,mean_ms:24.2849938,p50_ms:24.206858,p95_ms:24.7517102,p99_ms:26.7518376,throughput_ops_s:409.5892957},
  {mode:"synthetic",scenario:"read_path",concurrency:25,n:500,success_rate:1,mean_ms:24.8489459,p50_ms:24.8992105,p95_ms:25.2209404,p99_ms:25.5873542,throughput_ops_s:993.102857},
  {mode:"synthetic",scenario:"approval_path",concurrency:1,n:500,success_rate:1,mean_ms:36.2496078,p50_ms:36.2158685,p95_ms:36.6002761,p99_ms:36.9663981,throughput_ops_s:27.5498848},
  {mode:"synthetic",scenario:"approval_path",concurrency:5,n:500,success_rate:1,mean_ms:36.465209,p50_ms:36.4093995,p95_ms:36.9233767,p99_ms:37.2048376,throughput_ops_s:136.7540108},
  {mode:"synthetic",scenario:"approval_path",concurrency:10,n:500,success_rate:1,mean_ms:36.8739975,p50_ms:36.785145,p95_ms:37.5188199,p99_ms:38.8210407,throughput_ops_s:270.0259011},
  {mode:"synthetic",scenario:"approval_path",concurrency:25,n:500,success_rate:1,mean_ms:37.4719952,p50_ms:37.43851,p95_ms:37.7324612,p99_ms:39.9345351,throughput_ops_s:661.8603235},
];
