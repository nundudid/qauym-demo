import { useMutation, useQueryClient } from '@tanstack/react-query';
import { useId, useState, type FormEvent, type KeyboardEvent } from 'react';
import { useOutletContext } from 'react-router-dom';
import { api, errorMessage } from '../api/client';
import type { Me } from '../api/types';
import { btnPrimary, btnSecondary, card, Field, inputClass, Notice } from '../components/ui';
import { ME_KEY } from '../hooks/useMe';
import { BIO_MAX, DISPLAY_NAME_MAX, MAX_INTERESTS, TAG_MAX } from '../validation';

export default function EditProfilePage() {
  const me = useOutletContext<Me>();
  const id = useId();
  const queryClient = useQueryClient();
  const [displayName, setDisplayName] = useState(me.display_name);
  const [bio, setBio] = useState(me.bio);
  const [interests, setInterests] = useState(me.interests);
  const [tag, setTag] = useState('');
  const [tagError, setTagError] = useState('');

  const save = useMutation({
    mutationFn: () =>
      api<Me>('/me', {
        method: 'PATCH',
        body: { display_name: displayName, bio, interests },
      }),
    onSuccess: (updated) => {
      queryClient.setQueryData(ME_KEY, updated);
      setInterests(updated.interests);
      return Promise.all([
        queryClient.invalidateQueries({ queryKey: ['profile'] }),
        queryClient.invalidateQueries({ queryKey: ['posts'] }),
      ]);
    },
  });

  const nameError = !displayName.trim()
    ? 'Enter a display name.'
    : displayName.trim().length > DISPLAY_NAME_MAX
      ? `Use at most ${DISPLAY_NAME_MAX} characters.`
      : '';
  const bioTooLong = bio.length > BIO_MAX;

  function addTag() {
    const value = tag.trim().toLowerCase();
    if (!value) return;
    if (value.length > TAG_MAX) return setTagError(`Use at most ${TAG_MAX} characters.`);
    if (interests.includes(value)) return setTagError('You already added that interest.');
    if (interests.length >= MAX_INTERESTS)
      return setTagError(`You can add up to ${MAX_INTERESTS} interests.`);
    setInterests([...interests, value]);
    setTag('');
    setTagError('');
    save.reset();
  }

  function onTagKey(event: KeyboardEvent<HTMLInputElement>) {
    if (event.key === 'Enter') {
      event.preventDefault(); // Enter adds the tag instead of saving the form
      addTag();
    }
  }

  function submit(event: FormEvent) {
    event.preventDefault();
    if (!nameError && !bioTooLong) save.mutate();
  }

  return (
    <>
      <h1 className="mb-4 text-2xl font-semibold">Edit profile</h1>
      <form onSubmit={submit} noValidate className={`${card} space-y-4`}>
        <Field
          label="Display name"
          value={displayName}
          onChange={(e) => setDisplayName(e.target.value)}
          error={nameError}
        />

        <div>
          <label htmlFor={`${id}-bio`} className="block text-sm font-medium">
            Bio
          </label>
          <textarea
            id={`${id}-bio`}
            rows={3}
            className={inputClass}
            value={bio}
            onChange={(e) => setBio(e.target.value)}
            aria-describedby={`${id}-bio-count`}
            aria-invalid={bioTooLong || undefined}
          />
          <p
            id={`${id}-bio-count`}
            className={`mt-1 text-sm ${bioTooLong ? 'text-red-800' : 'text-slate-600'}`}
          >
            {bio.length} / {BIO_MAX} characters{bioTooLong && ' — too long'}
          </p>
        </div>

        <fieldset>
          <legend className="text-sm font-medium">
            Interests ({interests.length} of {MAX_INTERESTS})
          </legend>
          {interests.length > 0 && (
            <ul className="mt-2 flex flex-wrap gap-2">
              {interests.map((item) => (
                <li
                  key={item}
                  className="flex items-center gap-1 rounded-full border border-slate-400 py-0.5 pr-1 pl-2 text-sm"
                >
                  {item}
                  <button
                    type="button"
                    className="rounded-full px-1.5 font-bold hover:bg-slate-200"
                    aria-label={`Remove ${item}`}
                    onClick={() => {
                      setInterests(interests.filter((i) => i !== item));
                      setTagError('');
                    }}
                  >
                    ×
                  </button>
                </li>
              ))}
            </ul>
          )}
          <div className="mt-2 flex items-end gap-2">
            <div className="flex-1">
              <label htmlFor={`${id}-tag`} className="block text-sm">
                Add an interest
              </label>
              <input
                id={`${id}-tag`}
                className={inputClass}
                value={tag}
                onChange={(e) => setTag(e.target.value)}
                onKeyDown={onTagKey}
                aria-describedby={`${id}-tag-error`}
                aria-invalid={tagError ? true : undefined}
              />
            </div>
            <button type="button" className={btnSecondary} onClick={addTag}>
              Add
            </button>
          </div>
          <p id={`${id}-tag-error`} aria-live="polite" className="mt-1 text-sm text-red-800">
            {tagError && <>Error: {tagError}</>}
          </p>
        </fieldset>

        <button type="submit" className={btnPrimary} disabled={save.isPending}>
          {save.isPending ? 'Saving…' : 'Save profile'}
        </button>
        <Notice kind="status">{save.isSuccess && 'Profile saved.'}</Notice>
        <Notice kind="error">{save.isError && errorMessage(save.error)}</Notice>
      </form>
    </>
  );
}
