-- extract_cctp_burns.sql
-- Pull DepositForBurn events for one CCTP source chain.
--
-- DepositForBurn(uint64 indexed nonce, address indexed burnToken,
--                uint256 amount, address indexed depositor,
--                bytes32 mintRecipient, uint32 destinationDomain,
--                bytes32 destinationTokenMessenger, bytes32 destinationCaller)
-- topic[0] keccak256 = 0x2fa9ca894982930190727e75500a97d8dc500233a5065e0f3126c48fbe0343c0
-- topic[1] = nonce (uint64, padded to bytes32)
-- topic[2] = burnToken (address)
-- topic[3] = depositor (address)
-- data    = amount (32) + mintRecipient (32) + destinationDomain (32)
--           + destinationTokenMessenger (32) + destinationCaller (32) = 160 bytes
--
-- Parameters substituted by Python:
--   @logs_table     : fully qualified logs table for the source chain
--
-- BigQuery scalar parameters:
--   @start_ts                : lower bound on block_timestamp
--   @end_ts                  : upper bound on block_timestamp
--   @token_messenger_addr    : CCTP TokenMessenger contract address on source chain

SELECT
  block_timestamp,
  block_number,
  transaction_hash,
  log_index,
  topics,
  data
FROM @logs_table
WHERE block_timestamp >= @start_ts
  AND block_timestamp <  @end_ts
  AND LOWER(address) = LOWER(@token_messenger_addr)
  AND ARRAY_LENGTH(topics) >= 4
  AND topics[OFFSET(0)] = '0x2fa9ca894982930190727e75500a97d8dc500233a5065e0f3126c48fbe0343c0'
ORDER BY block_timestamp, log_index;
