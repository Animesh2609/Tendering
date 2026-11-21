1. **https://youtu.be/M7ywTw6o1Pk?si=K1BUS3fAbIoA5NXI**
2. **Install in Ubuntu:**

   * curl -sSLO https://raw.githubusercontent.com/hyperledger/fabric/main/scripts/install-fabric.sh
   * chmod +x install-fabric.sh
   * ./install-fabric.sh docker samples binary
3. *Allow Rights to Docker (USE MOBILE NET):*\*\*

   * sudo usermod -aG docker $USER
   * from other cmd admin: wsl --shutdown
   * reopen ubuntu: ./install-fabric.sh docker samples binary
4. Run Network:

   * cd fabric-samples/test-network
   * ./network.sh up
   * ./network.sh createChannel -c tenders
   * ./network.sh deployCC -c tenders -ccn basic \\
   * \-ccp /mnt/c/Users/SrijanWork/Documents/Coding/TenderBlock/PureTender/chaincode/puretender \\
   * \-ccl go
5. 
6. Create Crypto Folder under Resources, then copy and paste folder from HyperLedger running on Linux (content inside Test-Network) for certificates.

