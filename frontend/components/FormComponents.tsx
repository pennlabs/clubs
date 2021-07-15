import 'react-datepicker/dist/react-datepicker.css'

import { ContentState, convertToRaw, EditorState } from 'draft-js'
import draftToHtml from 'draftjs-to-html'
import { useField, useFormikContext } from 'formik'
import Head from 'next/head'
import React, {
  ReactElement,
  ReactNode,
  useContext,
  useEffect,
  useRef,
  useState,
} from 'react'
import DatePicker from 'react-datepicker'
import Select from 'react-select'
import styled from 'styled-components'
import uuid from 'uuid'

import { DynamicQuestion } from '../types'
import { titleize } from '../utils'
import AddressField from './ClubEditPage/AddressField'
import { Icon } from './common'
import EmbedOption, {
  blockRendererFunction,
  entityToHtml,
  htmlToEntity,
} from './EmbedOption'

/**
 * All form fields should accept these properties.
 *
 * The form fields should render with Bulma styling in mind.
 */
interface BasicFormField {
  id?: string
  name: string
  required?: boolean
  label?: string
  helpText?: string
  placeholder?: string
  noLabel?: boolean
}

/**
 * This interface allows for completely arbitrary props
 * to be passed to any of the form inputs.
 *
 * The ideal solution would be to explicitly define what
 * props each form field accepts.
 *
 * This is used for now so that we can at least guarantee
 * that a form field has the basic properties expected
 * of all form fields.
 */
interface AnyHack {
  [key: string]: any
}

const FormFieldClassContext = React.createContext<string>('')

/**
 * To style all fields inside of a Formik form, wrap all fields with this component.
 *
 * @param isHorizontal Use the Bulma horizontal layout for form fields.
 */
export const FormStyle = ({
  children,
  isHorizontal,
}: React.PropsWithChildren<{ isHorizontal?: boolean }>): ReactElement => {
  if (!isHorizontal) {
    return <>{children}</>
  }

  return (
    <FormFieldClassContext.Provider value="is-horizontal">
      {children}
    </FormFieldClassContext.Provider>
  )
}

type FieldWrapperProps = BasicFormField & { isError?: boolean }

/**
 * This field wrapper is used to automatically add labels and help texts
 * for most components. The components that use this wrapper only need
 * to specify the input itself.
 */
function useFieldWrapper<T extends FieldWrapperProps>(
  Element: React.ComponentType<Omit<T, 'label' | 'noLabel' | 'helpText'>>,
): (props: T) => ReactElement {
  return (props: T) => {
    const { label, noLabel, helpText, ...other } = props
    const { status } = useFormikContext()
    const actualLabel = label ?? titleize(props.name)
    const errorMessage = status && status[props.name]
    const fieldContext = useContext(FormFieldClassContext)
    const isHorizontal = fieldContext.includes('is-horizontal')

    const fieldLabel = (
      <label className="label" htmlFor={other.id}>
        {actualLabel}
        {props.required && <span style={{ color: 'red' }}>*</span>}
      </label>
    )

    const fieldBody = (
      <>
        <div className="control">
          <Element {...other} isError={!!errorMessage} />
        </div>
        <p className={`help ${errorMessage ? 'is-danger' : ''}`}>
          {errorMessage || helpText}
        </p>
      </>
    )

    return (
      <div className={`field ${fieldContext}`}>
        {noLabel ||
          (isHorizontal ? (
            <div className="field-label">{fieldLabel}</div>
          ) : (
            fieldLabel
          ))}
        {isHorizontal ? (
          <div className="field-body">
            <div className="field">{fieldBody}</div>
          </div>
        ) : (
          fieldBody
        )}
      </div>
    )
  }
}

/**
 * We can only initialize these properties on the client side.
 * Disable them for server side rendering or errors will be thrown.
 */
let htmlToDraft: any = null
let Editor: ((props: any) => ReactElement) | null = null
if (process.browser) {
  // eslint-disable-next-line @typescript-eslint/no-var-requires
  htmlToDraft = require('html-to-draftjs').default
  // eslint-disable-next-line @typescript-eslint/no-var-requires
  Editor = require('react-draft-wysiwyg').Editor
}

/**
 * A rich text editor that accepts and outputs HTML.
 */
export const RichTextField = useFieldWrapper(
  (props: BasicFormField & AnyHack): ReactElement => {
    const { setFieldValue } = useFormikContext()
    const textValue = useRef<string | null>(null)

    const [editorState, setEditorState] = useState<EditorState>(() =>
      EditorState.createEmpty(),
    )

    useEffect(() => {
      if (props.value !== textValue.current) {
        if (props.value && props.value.length) {
          setEditorState(
            EditorState.createWithContent(
              ContentState.createFromBlockArray(
                htmlToDraft(props.value, htmlToEntity).contentBlocks,
              ),
            ),
          )
        } else {
          setEditorState(EditorState.createEmpty())
        }
        textValue.current = props.value
      }
    }, [props.value])

    return (
      <div>
        <Head>
          <link
            href="/static/css/react-draft-wysiwyg.css"
            rel="stylesheet"
            key="editor-css"
          />
          <link
            href="/static/css/react-datepicker.css"
            rel="stylesheet"
            key="datepicker-css"
          />
        </Head>
        {Editor != null && (
          <Editor
            editorState={editorState}
            placeholder={props.placeholder}
            onEditorStateChange={(state): void => {
              setEditorState(state)
              const newValue = draftToHtml(
                convertToRaw(state.getCurrentContent()),
                undefined,
                undefined,
                entityToHtml,
              )
              textValue.current = newValue
              setFieldValue(props.name, newValue)
            }}
            toolbar={{
              options: [
                'inline',
                'fontSize',
                'fontFamily',
                'list',
                'textAlign',
                'colorPicker',
                'link',
                'image',
                'remove',
                'history',
              ],
            }}
            editorStyle={{
              border: '1px solid #dbdbdb',
              padding: '0 1em',
            }}
            toolbarCustomButtons={[<EmbedOption />]}
            customBlockRenderFunc={blockRendererFunction}
          />
        )}
      </div>
    )
  },
)

const DatePickerWrapper = styled.span`
  & .react-datepicker-wrapper {
    width: 100%;
  }

  & .react-datepicker-popper {
    z-index: 3;
  }
`

/**
 * A datetime field that allows the user to choose a date and a time.
 */
export const DateTimeField = useFieldWrapper(
  (props: BasicFormField & AnyHack): ReactElement => {
    const { name, value, placeholder, ...other } = props
    const { setFieldValue } = useFormikContext()

    return (
      <DatePickerWrapper>
        <DatePicker
          className="input"
          showTimeSelect
          dateFormat="MMMM d, yyyy h:mm aa"
          selected={Date.parse(value) || value}
          placeholderText={placeholder}
          {...other}
          onChange={(val) => {
            setFieldValue(name, val)
          }}
        />
      </DatePickerWrapper>
    )
  },
)

/**
 * A field that allows the user to enter an arbitrary line of text.
 */
const TextEditField = ({ field, setField }): ReactElement => {
  return (
    <div className="mb-3 box">
      <div className="mb-2">
        <b>Text Field:</b> The user can enter arbitrary text.
      </div>
      <input
        type="text"
        className="input"
        value={field.label}
        placeholder="Add your question here!"
        onChange={(e) => setField({ ...field, label: e.target.value })}
      />
      {['Text', 'Textarea', 'HTML'].map((type) => {
        const value = type.toLowerCase()

        return (
          <div>
            <label>
              <input
                type="radio"
                value={value}
                checked={value === field.type}
                onChange={(e) => setField({ ...field, type: e.target.value })}
              />{' '}
              {type}
            </label>
          </div>
        )
      })}
    </div>
  )
}

/**
 * A field that allows the user to specify a radio input field.
 */
const RadioEditField = ({ field, setField }): ReactElement => {
  return (
    <div className="mb-3 box">
      <div className="mb-2">
        <b>Radio Field:</b> The user can select a single choice from a list of
        choices.
      </div>
      <input
        type="text"
        className="input"
        value={field.label}
        placeholder="Add your question here!"
        onChange={(e) => setField({ ...field, label: e.target.value })}
      />
      <div className="content">
        <ul>
          {field.choices?.map(
            (choice: { id: string; label: string }, i: number) => (
              <li key={i}>
                <div className="level">
                  <div className="level-left">
                    [
                    <input
                      type="text"
                      className="input is-small"
                      value={choice.id}
                      placeholder="Value"
                      onChange={(e) => {
                        const newChoices = [...field.choices]
                        newChoices[i].id = e.target.value
                        setField({ ...field, choices: newChoices })
                      }}
                    />
                    ]{' '}
                  </div>
                  <div className="level-item">
                    <input
                      type="text"
                      className="input is-small"
                      value={choice.label}
                      placeholder="Label"
                      onChange={(e) => {
                        const newChoices = [...field.choices]
                        newChoices[i].label = e.target.value
                        setField({ ...field, choices: newChoices })
                      }}
                    />
                  </div>
                </div>
              </li>
            ),
          )}
          <li>
            <button
              type="button"
              className="button is-success is-small"
              onClick={() => {
                const newChoices = [...field.choices]
                newChoices.push({ id: '', label: '' })
                setField({ ...field, choices: newChoices })
              }}
            >
              <Icon name="plus" /> Add Choice
            </button>
          </li>
        </ul>
      </div>
    </div>
  )
}

/**
 * A field that allows users to make form fields.
 * Accepts and returns form fields in a serialized JSON format.
 */
export const DynamicQuestionField = useFieldWrapper(
  ({ name, value }: BasicFormField & AnyHack): ReactElement => {
    const { setFieldValue } = useFormikContext()

    const values: DynamicQuestion[] =
      (typeof value === 'string' ? JSON.parse(value) : value) ?? []

    const addField = (type: string): void => {
      values.push({
        name: uuid.v4(),
        label: '',
        type: type,
        choices: [],
      })
      setFieldValue(name, JSON.stringify(values))
    }

    return (
      <>
        {values.map((field: DynamicQuestion, i: number) => {
          let Class = TextEditField
          if (field.type === 'radio') {
            Class = RadioEditField
          }
          return (
            <Class
              key={i}
              field={field}
              setField={(field) => {
                values[i] = field
                setFieldValue(name, JSON.stringify(values))
              }}
            />
          )
        })}
        <div className="buttons">
          <button
            type="button"
            className="button is-success is-small"
            onClick={() => addField('radio')}
          >
            <Icon name="plus" /> Add Radio Field
          </button>
          <button
            type="button"
            className="button is-success is-small"
            onClick={() => addField('text')}
          >
            <Icon name="plus" /> Add Text Field
          </button>
        </div>
      </>
    )
  },
)

/**
 * A field that allows the user to type in text.
 * @param type This can be used to override the type of the text input (for example, you can specify "email" or "date"). If you specify "textarea", a textarea will be rendered instead.
 */
export const TextField = useFieldWrapper(
  (props: BasicFormField & AnyHack): ReactElement => {
    const {
      type = 'text',
      isError,
      value,
      customHandleChange,
      ...other
    } = props

    const { setFieldValue } = useFormikContext()

    // It turns out that URL fields confuse people because Chrome doesn't let you submit unless its a valid URL.
    // People don't include the https:// schema or enter something that isn't a URL, causing Chrome to reject these URLs.
    // We have some server side processing that is more flexible, so just turn URL fields into text fields for now.
    let actualType = type
    if (type === 'url') {
      actualType = 'text'
    }

    if (type === 'textarea') {
      return (
        <textarea
          className={`textarea ${isError ? 'is-danger' : ''}`}
          value={value ?? ''}
          {...other}
        ></textarea>
      )
    }

    if (type === 'radio') {
      return (
        <>
          {other.choices
            .map(({ id, label }) => (
              <label key={id} className="radio">
                <input
                  type="radio"
                  name={other.name}
                  value={id}
                  onChange={() => setFieldValue(other.name, id)}
                />{' '}
                {label}
              </label>
            ))
            .map((item: ReactNode, i: number) => [
              item,
              <br key={`break-${i}`} />,
            ])
            .flat()}
        </>
      )
    }

    return (
      <input
        className={`input ${isError ? 'is-danger' : ''}`}
        type={actualType}
        value={value != null ? value.toString() : ''}
        {...other}
      />
    )
  },
)

/**
 * A field that allows the user to upload a file.
 * If an image is uploaded, the image will be shown as a preview.
 *
 * @param isImage Whether or not this file upload field is intended to accept images.
 * @param canDelete Whether or not images can be deleted instead of just replaced.
 */
export const FileField = useFieldWrapper(
  ({
    name,
    placeholder,
    onBlur,
    value,
    isImage = false,
    canDelete = false,
  }: BasicFormField & AnyHack): ReactElement => {
    const { setFieldValue } = useFormikContext()

    const [imageUrl, setImageUrl] = useState<string | null>(null)
    const [newlyUploaded, setNewlyUploaded] = useState<boolean>(false)

    useEffect(() => {
      if (value === null) {
        setImageUrl(null)
        setNewlyUploaded(false)
      } else if (value instanceof File) {
        if (isImage) {
          const reader = new FileReader()
          reader.onload = (e) => {
            setImageUrl(e.target?.result as string)
          }
          reader.readAsDataURL(value)
          setNewlyUploaded(true)
        } else {
          setImageUrl(`FILE:${value.name}`)
        }
      } else {
        setImageUrl(value)
        setNewlyUploaded(false)
      }
    }, [value])

    return (
      <>
        {imageUrl &&
          (imageUrl.startsWith('FILE:') ? (
            <div className="mb-3">
              <Icon name="file" alt="file" /> {imageUrl.substr(5)}
            </div>
          ) : (
            <img style={{ maxWidth: 300 }} src={imageUrl} />
          ))}
        <div className="file">
          <label className="file-label">
            <input
              className="file-input"
              type="file"
              name={name}
              onChange={(e) => {
                if (e.target.files) {
                  setFieldValue(name, e.target.files[0])
                }
              }}
              onBlur={onBlur}
              placeholder={placeholder}
            />
            <span className="file-cta">
              <span className="file-label">
                Choose a {isImage ? 'image' : 'file'}...
              </span>
            </span>
          </label>
          {imageUrl && (canDelete || isImage) && (
            <button
              type="button"
              onClick={() => {
                setFieldValue(name, null)
              }}
              className="ml-3 button is-danger"
            >
              <Icon name="trash" /> Remove {isImage ? 'Image' : 'File'}
            </button>
          )}
        </div>
        {newlyUploaded && (
          <p className="is-size-7">(Submit this form to confirm upload)</p>
        )}
      </>
    )
  },
)

/**
 * A field that provides autosuggestions for address completion.
 *
 * If no Google API key is set, this will fall back to a text field.
 */
export const FormikAddressField = useFieldWrapper(
  (props: BasicFormField & AnyHack): ReactElement => {
    const { setFieldValue } = useFormikContext()
    return (
      <AddressField
        addressValue={props.value}
        changeAddress={(val) => setFieldValue(props.name, val)}
      />
    )
  },
)

type SelectFieldProps<T> = {
  name: string
  choices: T[]
  placeholder?: string
  value: string | T | T[]
  onBlur: () => void
  serialize?: (inpt: { value: string; label: string }) => T
  deserialize?: (inpt: T) => { value: string; label: string }
  valueDeserialize?: (
    inpt: string | T | T[],
  ) => typeof inpt extends Array<T>
    ? { value: string; label: string }[]
    : { value: string; label: string }
  formatOptionLabel: (inpt: any) => string | ReactElement
  isMulti?: boolean
  customHandleChange?: (updated: any) => void
}

/**
 * A field where you can select one or more tags from a list of tags.
 *
 * @param choices The choices that the user is allowed to select from.
 * @param isMulti If set to true, you can select more than one tag. Otherwise, you can only select one tag.
 */
export const SelectField = useFieldWrapper(
  ({
    name,
    choices,
    placeholder,
    value,
    onBlur,
    serialize,
    deserialize,
    valueDeserialize,
    isMulti,
    formatOptionLabel,
    customHandleChange,
  }: BasicFormField &
    SelectFieldProps<
      { [key: string]: string | number } | string
    >): ReactElement => {
    const { setFieldValue } = useFormikContext()

    /**
     * Convert from react-select format to the final value that is being set.
     */
    const actualSerialize = (opt) => {
      if (opt == null) {
        return isMulti ? [] : null
      }
      if (serialize == null) {
        if (choices.length > 0 && typeof choices[0] !== 'object') {
          serialize = ({ value }) => value
        } else {
          serialize = ({ value, label }) => ({
            id: value,
            name: label,
          })
        }
      }
      return Array.isArray(opt) ? opt.map(serialize) : serialize(opt)
    }

    /**
     * Convert from the props that were passed in to the format that react-select is expecting.
     */
    const actualDeserialize = (opt) => {
      if (opt == null) {
        return isMulti ? [] : null
      }
      if (deserialize == null) {
        deserialize = (item) => {
          if (typeof item === 'object') {
            return {
              value: (item.id ?? item.value) as string,
              label: (item.name ?? item.label) as string,
            }
          }
          return {
            value: item,
            label: item,
          }
        }
      }
      return Array.isArray(opt) ? opt.map(deserialize) : deserialize(opt)
    }

    return (
      <Select
        instanceId={name}
        key={name}
        placeholder={placeholder}
        isMulti={isMulti}
        value={(valueDeserialize ?? actualDeserialize)(value)}
        options={
          actualDeserialize(choices) as {
            label: string | ReactElement
            value: string
          }[]
        }
        formatOptionLabel={formatOptionLabel}
        onChange={(opt): void => {
          setFieldValue(name, actualSerialize(opt))
          if (customHandleChange !== undefined) {
            customHandleChange(opt)
          }
        }}
        onBlur={onBlur}
        styles={{ container: (style) => ({ ...style, width: '100%' }) }}
      />
    )
  },
)

/**
 * A field that renders a single checkbox with a label.
 */
export const CheckboxField = (
  props: BasicFormField & AnyHack,
): ReactElement => {
  const { label, value, onChange, helpText, ...other } = props
  const { status, setFieldValue } = useFormikContext()
  const errorMessage = status && status[props.name]
  const fieldContext = useContext(FormFieldClassContext)
  const isHorizontal = fieldContext.includes('is-horizontal')

  const innerBody = (
    <>
      <div className="control">
        <label className="checkbox">
          <input
            type="checkbox"
            checked={value}
            {...other}
            onChange={(e) => {
              setFieldValue(props.name, e.target.checked)
            }}
          />{' '}
          {label}
        </label>
      </div>
      {helpText && <p className="help">{helpText}</p>}
      {errorMessage && <p className="help is-danger">{errorMessage}</p>}
    </>
  )

  return (
    <div className={`field ${fieldContext}`}>
      {isHorizontal ? (
        <>
          <div className="field-label">
            <label className="label">{titleize(props.name)}</label>
          </div>
          <div className="field-body">{innerBody}</div>
        </>
      ) : (
        innerBody
      )}
    </div>
  )
}

export const CheckboxTextField: React.FC<BasicFormField & AnyHack> = (
  props,
) => {
  const { label, onChange, textRequired, ...other } = props
  const fieldContext = useContext(FormFieldClassContext)
  const [input, meta, helpers] = useField({
    name: props.name,
    validate: (value) => {
      if (
        !!textRequired &&
        value?.checked &&
        (!value?.detail || value?.detail?.length === 0)
      ) {
        return textRequired
      }
      return null
    },
  })

  const value = meta.value || props.value

  return (
    <>
      <div
        className={`field ${fieldContext}`}
        style={{ display: 'flex', alignItems: 'center' }}
      >
        <div className="control">
          <label className="checkbox">
            <input
              type="checkbox"
              style={{ transform: 'scale(1.5)' }}
              checked={value?.checked ?? false}
              onChange={(e) =>
                helpers.setValue({
                  ...value,
                  checked: e.target.checked,
                })
              }
            />{' '}
            <span style={{ display: 'inline-block', marginLeft: '8px' }}>
              {label}
            </span>
          </label>
        </div>
        <div className="field-text" style={{ marginLeft: '8px', flex: 1 }}>
          <input
            type="text"
            className="input"
            style={{ width: '100%' }}
            value={value?.detail ?? ''}
            onChange={(e) =>
              helpers.setValue({ ...value, detail: e.target.value })
            }
          />
        </div>
      </div>
      {meta.error && (
        <p className="help is-danger" style={{ marginBottom: '8px' }}>
          {meta.error}
        </p>
      )}
    </>
  )
}
