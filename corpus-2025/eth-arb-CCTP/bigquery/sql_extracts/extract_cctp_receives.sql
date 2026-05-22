-- extract_cctp_receives.sql
-- Pull MessageReceived events for one CCTP destination chain.
--
-- MessageReceived(address indexed caller, uint32 sourceDomain,
--                 uint64 indexed nonce, bytes32 sender, bytes messageBody)
-- topic[0] keccak256 = 0x58200b4c34ae05ee816d710053fff3fb75af4395915d3d2a771b24aa10e3cc5d
-- (verified empirically via smoke_cctp.py against V1 MessageTransmitter on Arbitrum)
-- topic[1] = caller (address, padded)
-- topic[2] = nonce (uint64, padded)
-- data    = sourceDomain (32) + sender (32) + messageBody offset (32)
--           + messageBody length (32) + messageBody bytes (variable)
--
-- Parameters substituted by Python:
--   @logs_table     : fully qualified logs table for the destination chain
--
-- BigQuery scalar parameters:
--   @start_ts                  : lower bound on block_timestamp
--   @end_ts                    : upper bound on block_timestamp
--   @message_transmitter_addr  : CCTP MessageTransmitter contract address on destination chain

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
  AND LOWER(address) = LOWER(@message_transmitter_addr)
  AND ARRAY_LENGTH(topics) >= 3
  AND topics[OFFSET(0)] = '0x58200b4c34ae05ee816d710053fff3fb75af4395915d3d2a771b24aa10e3cc5d'
ORDER BY block_timestamp, log_index;
