solc-select use 0.4.5  &> /dev/null
solc ./scripts/solidity_tests/solc045_success.sol

if [[ $? != 0 ]]; then
  echo "FAILED: solc045_success" $?
  exit 255
fi
echo "SUCCESS: solc045_success"

execute=$(solc ./scripts/solidity_tests/solc045_fail_compile.sol 2>&1)
if [[ "$execute" != *"Error: Expected token Semicolon got 'Function'"* ]]; then
  echo "FAILED: solc045_fail_compile"
  echo "$execute"
  exit 255
fi
echo "SUCCESS: solc045_fail_compile"

solc-select use 0.5.0  &> /dev/null
solc ./scripts/solidity_tests/solc050_success.sol

if [[ $? != 0 ]]; then
  echo "FAILED: solc050_success" $?
  exit 255
fi
echo "SUCCESS: solc050_success"

execute=$(solc ./scripts/solidity_tests/solc050_fail_compile.sol 2>&1)
if [[ "$execute" != *"Error: Functions are not allowed to have the same name as the contract."* ]]; then
  echo "FAILED: solc045_fail_compile"
  echo "$execute"
  exit 255
fi
echo "SUCCESS: solc045_fail_compile"
