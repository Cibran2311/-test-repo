// Lab 11 / Mission 11 - Dissect a Jetton Transfer.
//
// Deploys a Jetton Master, mints jettons, transfers some to another wallet, and
// then dissects the resulting message chain to show the TON token architecture:
//
//   Jetton Master  ->  Jetton Wallet (holder A)
//                  ->  Jetton Wallet (holder B)
//
// Unlike ERC20, no single contract holds every balance. Each holder gets their
// own Jetton Wallet contract, and a transfer is a chain of internal messages
// between those contracts.
//
// The lab expects an instructor-provided Jetton Master. It is not published in
// this repository, so this script deploys its own using the standard jetton
// contracts shipped with @ton-community/assets-sdk.
//
// Run:  node run_lab11.mjs

import { Address, Cell, Dictionary, beginCell, toNano, fromNano } from '@ton/core';
import { JettonMinter, JettonWallet } from '@ton-community/assets-sdk';
import { sha256_sync } from '@ton/crypto';
import { readFileSync, writeFileSync } from 'fs';
import { join } from 'path';
import { KEYS_DIR, getClient, rl, sleep, loadWallet, addr, waitForSeqno, EXPLORER }
  from '../_shared/ton.mjs';

const JETTON_NAME = 'Student Jetton';
const JETTON_SYMBOL = 'SJET';
const JETTON_DECIMALS = 9;
const MINT_AMOUNT = 1000n;
const TRANSFER_AMOUNT = 25n;

/** TEP-64 on-chain metadata: prefix 0x00, then a dict keyed by sha256(attribute). */
function buildOnchainContent(fields) {
  const dict = Dictionary.empty(Dictionary.Keys.BigUint(256), Dictionary.Values.Cell());
  for (const [key, value] of Object.entries(fields)) {
    const keyHash = BigInt('0x' + sha256_sync(key).toString('hex'));
    // 0x00 prefix marks "snake" encoding of the value
    dict.set(keyHash, beginCell().storeUint(0, 8).storeStringTail(value).endCell());
  }
  return beginCell().storeUint(0, 8).storeDict(dict).endCell();
}

async function main() {
  const client = getClient();
  const { wallet, key } = await loadWallet();
  const recipient = JSON.parse(readFileSync(join(KEYS_DIR, 'ton_recipient.json'), 'utf8'));
  const recipientAddress = Address.parse(recipient.address_bounceable);

  const walletContract = client.open(wallet);
  const sender = walletContract.sender(key.secretKey);
  const myAddress = wallet.address;

  console.log('=== Step 1 - the wallet ===');
  console.log('  owner wallet   :', addr(myAddress));
  console.log('  balance        :', fromNano(await rl(() => client.getBalance(myAddress))), 'TON');

  // --------------------------------------------------- deploy the Jetton Master
  console.log('\n=== Step 2 - deploy the Jetton Master ===');
  const content = buildOnchainContent({
    name: JETTON_NAME,
    symbol: JETTON_SYMBOL,
    decimals: String(JETTON_DECIMALS),
    description: 'Lab 11 jetton for the blockchain course',
  });

  const minter = JettonMinter.createFromConfig({
    admin: myAddress,
    content,
    jettonWalletCode: JettonWallet.code,
  });
  const minterAddress = minter.address;
  console.log('  Jetton Master  :', addr(minterAddress));

  const minterOpened = client.open(minter);
  let seqno = await rl(() => walletContract.getSeqno(), 'getSeqno');
  await rl(() => minterOpened.sendDeploy(sender, toNano('0.1')), 'sendDeploy');
  await waitForSeqno(walletContract, seqno);
  console.log('\n  deployed, waiting for the contract to become active...');

  for (let i = 0; i < 20; i++) {
    await sleep(3000);
    const state = await rl(() => client.getContractState(minterAddress), 'getContractState');
    if (state.state === 'active') { console.log('  state          : active'); break; }
    process.stdout.write(`\r  state: ${state.state} (${(i + 1) * 3}s)`);
  }

  // --------------------------------------------------------------- mint
  console.log('\n=== Step 3 - mint jettons to the owner ===');
  const mintUnits = MINT_AMOUNT * 10n ** BigInt(JETTON_DECIMALS);
  seqno = await rl(() => walletContract.getSeqno(), 'getSeqno');
  await rl(() => minterOpened.sendMint(sender, myAddress, mintUnits, { value: toNano('0.1') }),
           'sendMint');
  await waitForSeqno(walletContract, seqno);
  console.log(`\n  minted ${MINT_AMOUNT} ${JETTON_SYMBOL}`);

  await sleep(8000);
  const data = await rl(() => minterOpened.getData(), 'getData');
  console.log('  total supply   :', (data.totalSupply / 10n ** BigInt(JETTON_DECIMALS)).toString(),
              JETTON_SYMBOL);
  console.log('  admin          :', data.adminAddress ? addr(data.adminAddress) : 'none');
  console.log('  mintable       :', data.mintable);

  // ------------------------------------------- the two Jetton Wallet addresses
  console.log('\n=== Step 3 - Jetton Wallet addresses (the key TON difference) ===');
  const myJettonWallet = await rl(() => minterOpened.getWalletAddress(myAddress),
                                  'getWalletAddress');
  const recipientJettonWallet = await rl(() => minterOpened.getWalletAddress(recipientAddress),
                                         'getWalletAddress');
  console.log('  owner TON wallet          :', addr(myAddress));
  console.log('  owner Jetton Wallet       :', addr(myJettonWallet), '  <- different contract');
  console.log('  recipient TON wallet      :', addr(recipientAddress));
  console.log('  recipient Jetton Wallet   :', addr(recipientJettonWallet));

  const myJW = client.open(JettonWallet.createFromAddress(myJettonWallet));
  const before = await rl(() => myJW.getData(), 'getData');
  console.log('  owner jetton balance      :',
              (before.balance / 10n ** BigInt(JETTON_DECIMALS)).toString(), JETTON_SYMBOL);

  // --------------------------------------------------------------- transfer
  console.log('\n=== Step 4 - send jettons ===');
  const transferUnits = TRANSFER_AMOUNT * 10n ** BigInt(JETTON_DECIMALS);
  seqno = await rl(() => walletContract.getSeqno(), 'getSeqno');
  await rl(() => myJW.send(sender, recipientAddress, transferUnits, {
    value: toNano('0.1'),
    notify: { amount: toNano('0.01') },
  }), 'jetton transfer');
  await waitForSeqno(walletContract, seqno);
  console.log(`\n  sent ${TRANSFER_AMOUNT} ${JETTON_SYMBOL} to ${addr(recipientAddress)}`);

  await sleep(12000);

  // --------------------------------------------------------------- inspect
  console.log('\n=== Step 5 - inspect the message trace ===');
  const txs = await rl(() => client.getTransactions(myJettonWallet, { limit: 5 }),
                       'getTransactions');
  const transferTx = txs[0];
  const hashHex = transferTx.hash().toString('hex');
  console.log('  transaction on the owner Jetton Wallet:');
  console.log('    hash         :', hashHex);
  console.log('    lt           :', transferTx.lt.toString());
  console.log('    in message   : from', transferTx.inMessage?.info?.src
    ? addr(transferTx.inMessage.info.src) : 'external');
  console.log('    out messages :', transferTx.outMessages.size);
  for (const [, msg] of transferTx.outMessages) {
    if (msg.info.type === 'internal') {
      console.log('      ->', addr(msg.info.dest), 'value', fromNano(msg.info.value.coins), 'TON');
    }
  }

  const afterOwner = await rl(() => myJW.getData(), 'getData');
  const recipientJW = client.open(JettonWallet.createFromAddress(recipientJettonWallet));
  let afterRecipient;
  try {
    afterRecipient = await rl(() => recipientJW.getData(), 'getData');
  } catch {
    afterRecipient = { balance: 0n };
  }

  const unit = 10n ** BigInt(JETTON_DECIMALS);
  console.log('\n=== Balances after ===');
  console.log('  owner Jetton Wallet     :', (afterOwner.balance / unit).toString(), JETTON_SYMBOL);
  console.log('  recipient Jetton Wallet :', (afterRecipient.balance / unit).toString(), JETTON_SYMBOL);

  if (afterOwner.balance !== (MINT_AMOUNT - TRANSFER_AMOUNT) * unit) {
    console.log('  WARNING: owner balance does not match the expected value');
  }
  if (afterRecipient.balance !== TRANSFER_AMOUNT * unit) {
    console.log('  WARNING: recipient balance does not match the expected value');
  }

  const explanation =
    'In TON each holder owns a separate Jetton Wallet contract. The Jetton ' +
    'Master stores only the metadata, the total supply and the code used to ' +
    'derive holder wallets; it never stores balances. A transfer is therefore ' +
    'not one contract updating a mapping, as in ERC20, but a chain of internal ' +
    'messages: the owner TON wallet sends a transfer message to its own Jetton ' +
    'Wallet, that contract deducts the amount and sends an internal_transfer ' +
    "message to the recipient's Jetton Wallet, which credits the balance and " +
    'sends back excess TON. Each Jetton Wallet address is deterministic, derived ' +
    'from the Master address plus the owner address, which is why it can be ' +
    'computed before the contract even exists. This design fits the sharded, ' +
    'asynchronous architecture of TON: two holders in different shards never ' +
    'contend for one shared storage slot.';

  const result = {
    labs: {
      lab11: {
        network: 'ton_testnet',
        ton_wallet: addr(myAddress),
        jetton_master: addr(minterAddress),
        jetton_name: JETTON_NAME,
        jetton_symbol: JETTON_SYMBOL,
        jetton_decimals: JETTON_DECIMALS,
        total_supply: (data.totalSupply / unit).toString(),
        sender_jetton_wallet: addr(myJettonWallet),
        recipient_jetton_wallet: addr(recipientJettonWallet),
        recipient_ton_wallet: addr(recipientAddress),
        transfer_amount: TRANSFER_AMOUNT.toString(),
        tx_hash_hex: hashHex,
        tx_link: `${EXPLORER}/transaction/${hashHex}`,
        explorer_jetton_master: `${EXPLORER}/${addr(minterAddress)}`,
        explorer_sender_jetton_wallet: `${EXPLORER}/${addr(myJettonWallet)}`,
        owner_balance_after: (afterOwner.balance / unit).toString(),
        recipient_balance_after: (afterRecipient.balance / unit).toString(),
        explanation,
        substitution_note:
          'the Jetton Master is deployed by this script using the standard jetton ' +
          'contracts; the lab defers the class Jetton Master address to the instructor',
      },
    },
  };
  writeFileSync('result.json', JSON.stringify(result, null, 2));
  console.log('\nwrote result.json');
}

main().catch((e) => {
  console.error('FAILED:', e.message);
  process.exit(1);
});
