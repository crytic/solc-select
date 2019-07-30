cd $(dirname "$0")

rm -r ./solc-select
mkdir solc-select
cp -r ../* solc-select || true

IMAGE_NAME=test-solc-select
docker build -t $IMAGE_NAME .
docker run $IMAGE_NAME
RETURN_CODE=$?

docker image rm $IMAGE_NAME
rm -r ./solc-select

exit $RETURN_CODE
