## solc 0.4.5 ##
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

## solc 0.5.0 ##
solc-select use 0.5.0  &> /dev/null
solc ./scripts/solidity_tests/solc050_success.sol

if [[ $? != 0 ]]; then
  echo "FAILED: solc050_success" $?
  exit 255
fi
echo "SUCCESS: solc050_success"

execute=$(solc ./scripts/solidity_tests/solc050_fail_compile.sol 2>&1)
if [[ "$execute" != *"Error: Functions are not allowed to have the same name as the contract."* ]]; then
  echo "FAILED: solc050_fail_compile"
  exit 255
fi
echo "SUCCESS: solc050_fail_compile"

## solc 0.6.0 ##
solc-select use 0.6.0  &> /dev/null
solc ./scripts/solidity_tests/solc060_success_trycatch.sol

if [[ $? != 0 ]]; then
  echo "FAILED: solc060_success_trycatch" $?
  exit 255
fi
echo "SUCCESS: solc060_success_trycatch"

solc ./scripts/solidity_tests/solc060_success_receive.sol

if [[ $? != 0 ]]; then
  echo "FAILED: solc060_success_receive" $?
  exit 255
fi
echo "SUCCESS: solc060_success_receive"

## solc 0.7.0 ##
solc-select use 0.7.0  &> /dev/null

execute=$(solc ./scripts/solidity_tests/solc070_fail_compile.sol 2>&1)
if [[ "$execute" != *"\"now\" has been deprecated."* ]]; then
  echo "FAILED: solc070_fail_compile" "$execute"
  exit 255
fi
echo "SUCCESS: solc070_fail_compile"

solc ./scripts/solidity_tests/solc070_success.sol

if [[ $? != 0 ]]; then
  echo "FAILED: solc070_success" $?
  exit 255
fi
echo "SUCCESS: solc070_success"

## solc 0.8.0 ##
solc-select use 0.8.0  &> /dev/null
solc ./scripts/solidity_tests/solc080_success.sol

if [[ $? != 0 ]]; then
  echo "FAILED: solc080_success" $?
  exit 255
fi
echo "SUCCESS: solc080_success"

execute=$(solc ./scripts/solidity_tests/solc080_success_warning.sol 2>&1)
if [[ "$execute" != *"Warning: Function state mutability can be restricted to pure"* ]]; then
  echo "FAILED: solc080_success_warning"
  exit 255
fi
echo "SUCCESS: solc080_success_warning"

execute=$(solc ./scripts/solidity_tests/solc080_fail_compile.sol 2>&1)
if [[ "$execute" != *"Error: Explicit type conversion not allowed"* ]]; then
  echo "FAILED: solc080_fail_compile"
  exit 255
fi
echo "SUCCESS: solc080_fail_compile"
