// Lab 10 / Mission 10 - Enter TON.
//
// Sends 0.01 TON on TON testnet and records the transaction for grading.
//
// Two TON specifics show up here:
//   * the wallet is a smart contract, and it is deployed lazily by its first
//     outgoing message, so the very first transfer also carries the wallet's
//     state init;
//   * the first transfer to a fresh address should use the non-bounceable form
//     (0Q...), otherwise the coins bounce back from an uninitialised account.
//
// The lab defers the recipient to the instructor; until that address is known
// the transfer targets a stand-in testnet wallet.
//
// Run:  node run_lab10.mjs

import { WalletContractV4, internal, toNano, fromNano, Address } from '@ton/ton';
import { mnemonicNew, mnemonicToPrivateKey } from '@ton/crypto';
import { readFileSync, writeFileSync, existsSync, chmodSync } from 'fs';
import { join } from 'path';
import { KEYS_DIR as KEYS, getClient, rl, sleep, loadWallet, addr, waitForSeqno, EXPLORER }
  from '../_shared/ton.mjs';

const RECIPIENT_FILE = join(KEYS, 'ton_recipient.json');
const AMOUNT = '0.01';

async function ensureRecipient() {
  if (existsSync(RECIPIENT_FILE)) {
    return JSON.parse(readFileSync(RECIPIENT_FILE, 'utf8'));
  }
  const mnemonic = await mnemonicNew(24);
  const key = await mnemonicToPrivateKey(mnemonic);
  const wallet = WalletContractV4.create({ workchain: 0, publicKey: key.publicKey });
  const payload = {
    network: 'ton_testnet',
    role: 'lab 10 stand-in recipient',
    address_bounceable: wallet.address.toString({ testOnly: true, bounceable: true }),
    address_non_bounceable: wallet.address.toString({ testOnly: true, bounceable: false }),
    mnemonic: mnemonic.join(' '),
    warning: 'TESTNET ONLY',
  };
  writeFileSync(RECIPIENT_FILE, JSON.stringify(payload, null, 2));
  chmodSync(RECIPIENT_FILE, 0o600);
  console.log(`  created a stand-in recipient, secret stored at ${RECIPIENT_FILE}`);
  return payload;
}

async function main() {
  const client = getClient();
  const { wallet, key } = await loadWallet();
  const recipient = await ensureRecipient();

  const contract = client.open(wallet);
  const address = addr(wallet.address);

  console.log('=== Step 1-3 - the wallet ===');
  console.log('  version        : WalletContractV4');
  console.log('  address        :', address);
  console.log('  raw form       :', wallet.address.toRawString());

  const stateBefore = await rl(() => client.getContractState(wallet.address), 'getContractState');
  const balanceBefore = await rl(() => client.getBalance(wallet.address), 'getBalance');
  console.log('  state          :', stateBefore.state);
  console.log('  balance        :', fromNano(balanceBefore), 'TON');
  if (stateBefore.state !== 'active') {
    console.log('  note           : the wallet contract is not deployed yet;');
    console.log('                   this first transfer carries its state init');
  }

  console.log('\n=== Step 4 - send the transfer ===');
  console.log('  to             :', recipient.address_non_bounceable, '(non-bounceable)');
  console.log('  amount         :', AMOUNT, 'TON');

  const seqnoBefore = await rl(() => contract.getSeqno(), 'getSeqno');
  console.log('  seqno before   :', seqnoBefore);

  await rl(() => contract.sendTransfer({
    secretKey: key.secretKey,
    seqno: seqnoBefore,
    messages: [
      internal({
        to: Address.parse(recipient.address_non_bounceable),
        value: toNano(AMOUNT),
        body: 'Lab 10 - first TON transfer',
        bounce: false,
      }),
    ],
  }), 'sendTransfer');
  console.log('  submitted, waiting for the seqno to advance...');

  const seqnoAfter = await waitForSeqno(contract, seqnoBefore);
  console.log(`\n  seqno after    : ${seqnoAfter}`);

  console.log('\n=== Step 5 - read the transaction back ===');
  await sleep(4000);
  const txs = await rl(() => client.getTransactions(wallet.address, { limit: 3 }), 'getTransactions');
  const tx = txs[0];
  const hashHex = tx.hash().toString('hex');
  const hashB64 = tx.hash().toString('base64');
  console.log('  lt             :', tx.lt.toString());
  console.log('  hash (hex)     :', hashHex);
  console.log('  now            :', new Date(tx.now * 1000).toISOString());
  console.log('  out messages   :', tx.outMessages.size);

  for (const [, msg] of tx.outMessages) {
    if (msg.info.type === 'internal') {
      console.log('    -> to        :', msg.info.dest.toString({ testOnly: true, bounceable: false }));
      console.log('       value     :', fromNano(msg.info.value.coins), 'TON');
      console.log('       bounce    :', msg.info.bounce);
    }
  }

  const stateAfter = await rl(() => client.getContractState(wallet.address), 'getContractState');
  const balanceAfter = await rl(() => client.getBalance(wallet.address), 'getBalance');
  const recipientBalance = await rl(
    () => client.getBalance(Address.parse(recipient.address_bounceable)), 'getBalance');
  console.log('\n=== Balances after ===');
  console.log('  sender state   :', stateAfter.state, '(was', stateBefore.state + ')');
  console.log('  sender balance :', fromNano(balanceBefore), '->', fromNano(balanceAfter), 'TON');
  console.log('  recipient      :', fromNano(recipientBalance), 'TON');

  if (fromNano(recipientBalance) !== AMOUNT) {
    console.log('  note: recipient balance differs from the sent amount only if fees');
    console.log('        were deducted on delivery');
  }

  const txLink = `${EXPLORER}/transaction/${hashHex}`;
  const result = {
    labs: {
      lab10: {
        network: 'ton_testnet',
        ton_wallet: address,
        wallet_version: 'WalletContractV4',
        recipient: recipient.address_bounceable,
        recipient_non_bounceable: recipient.address_non_bounceable,
        amount_ton: AMOUNT,
        tx_hash_hex: hashHex,
        tx_hash_base64: hashB64,
        logical_time: tx.lt.toString(),
        tx_link: txLink,
        explorer_wallet: `${EXPLORER}/${address}`,
        sender_state_before: stateBefore.state,
        sender_state_after: stateAfter.state,
        recipient_note:
          'stand-in testnet wallet; replace with the instructor address when it is published',
        ton_note:
          'the wallet is a contract deployed by its own first outgoing message; the ' +
          'transfer used the non-bounceable recipient form because the destination ' +
          'account did not exist yet',
      },
    },
  };
  writeFileSync('result.json', JSON.stringify(result, null, 2));
  console.log('\nwrote result.json');
  console.log('explorer:', txLink);
}

main().catch((e) => {
  console.error('FAILED:', e.message);
  process.exit(1);
});
