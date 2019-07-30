CODE=0

echo -n "Test version listing: "
COUNT=$(solc --versions | grep -e "0.[0-9]*.[0-9]*"| wc -l)
if [ $COUNT -lt 10 ]; then
	echo "Error"
	CODE=1
else
	echo "Passed"
fi

echo -n "Test running default version: "
solc --version | grep -q "Version: "
if [ ! $? = 0 ]; then
	echo "Error"
	CODE=1
else
	echo "Passed"
fi

echo -n "Test running specified version: "
SOME_VERSION=$(solc --versions | sed -n "6p")
SOLC_VERSION=$SOME_VERSION solc --version | grep -q "Version: $SOME_VERSION"
if [ ! $? = 0 ]; then
	echo "Error"
	CODE=1
else
	echo "Passed"
fi

exit $CODE
