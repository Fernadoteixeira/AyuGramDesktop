import { AyuGramApi } from './index'

declare global {
  interface Window {
    ayugramApi: AyuGramApi
  }
}
