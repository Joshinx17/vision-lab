import React from 'react';
import './resources.css';

export default function ResourcePanel({ resources, error, moduleId, refresh, selectProfile }) {
  const current = resources?.modules?.[moduleId];
  const active = resources?.profiles?.find(profile => profile.id === resources.active_sign_profile);
  return <section className="panel resource-panel" aria-label="Models and resources">
    <h2>Models & resources</h2>
    <button onClick={refresh}>Refresh resources</button>
    {error && <p role="alert">{error}</p>}
    {resources?.error && <p role="alert">{resources.error}</p>}
    {!resources && !error && <p>Checking required files…</p>}
    {current && <p className={current.ready ? 'resource-ready' : 'warning'}>
      {current.ready ? 'Required files found · runtime validation happens on start' : 'This module needs attention'}
    </p>}
    {current?.issues?.map(issue => <p className="warning" key={issue}>{issue}</p>)}
    {moduleId === 'sign_language' && resources?.warnings?.map(warning => <p className="warning" key={warning}>{warning}</p>)}
    {moduleId === 'air_write' && !current?.ready && <p>Mouse / touch drawing remains available.</p>}
    <label>Sign model profile<select value={resources?.active_sign_profile || ''} onChange={event => selectProfile(event.target.value)} disabled={!resources?.profiles?.length || resources.training === 'running'}>
      {!resources?.profiles?.length && <option value="">No valid catalog loaded</option>}
      {resources?.profiles?.map(profile => <option value={profile.id} key={profile.id}>{profile.name}{profile.ready ? '' : ' · needs resources'}</option>)}
    </select></label>
    {active && <details><summary>Selected model contract</summary>
      <p>{active.description}</p><code>{active.path}</code>
      <p>Labels: <code>{active.labels_path || 'inline labels'}</code></p>
      <pre>{JSON.stringify({ adapter: active.adapter, input: active.input, classes: active.labels?.length, hand_crop: active.hand_crop }, null, 2)}</pre>
      {active.issues.map(issue => <p className="warning" key={issue}>{issue}</p>)}
    </details>}
    <p>Add or update files inside the project, edit <code>config/resources.json</code>, then apply a profile. Missing model slots stay empty.</p>
    <button disabled={!active || resources?.training === 'running'} onClick={() => selectProfile(resources.active_sign_profile)}>Apply / reload selected profile</button>
    {!resources?.reference?.ready && resources?.reference?.issue && <p>{resources.reference.issue}</p>}
    <small>Browser assets changed in frontend/public require a rebuild and page reload. Arbitrary model architectures require their own adapter.</small>
  </section>;
}
