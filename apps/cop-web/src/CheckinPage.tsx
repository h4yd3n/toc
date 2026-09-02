import { useEffect, useState } from 'react'
import { checkInByToken } from './api'

/** /checkin/<token> — what the SMS or chat link opens. No login; the token is the credential. */
export default function CheckinPage({ token }: { token: string }) {
  const [state, setState] = useState<'idle' | 'sending' | 'done' | 'error'>('idle')
  const [msg, setMsg] = useState('')
  const [note, setNote] = useState('')
  useEffect(() => { document.title = 'TOC — Check in' }, [])
  const go = async () => {
    setState('sending')
    try { await checkInByToken(token, note || undefined); setState('done') }
    catch (e) { setState('error'); setMsg(String(e).includes('409') ? 'This roll call is already closed.' : String(e).includes('404') ? 'This link is not valid.' : String(e)) }
  }
  return (
    <div className="checkin-page">
      <div className="brand"><span className="mark">TOC</span><span className="sub">ROLL CALL</span></div>
      {state === 'done' ? <>
        <h1>✓ You're accounted for.</h1>
        <p>The watch floor has your status as <b>SAFE</b>. If that changes, call them.</p>
      </> : <>
        <h1>Are you safe?</h1>
        <p>Security is accounting for everyone. Tap once to confirm — that's all the floor needs.</p>
        <input placeholder="Optional: where you are / anything the floor should know" value={note} onChange={e => setNote(e.target.value)} />
        <button className="big" disabled={state === 'sending'} onClick={go}>{state === 'sending' ? 'SENDING…' : "I'M SAFE"}</button>
        <p className="dim">Need help? Don't use this page — call the watch floor.</p>
        {state === 'error' && <p className="err">{msg}</p>}
      </>}
    </div>)
}
