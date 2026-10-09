declare module 'virtual:opscope-configuration' {
  const Configuration: import('./types').ConfigAPI
  export default Configuration
}
declare module 'virtual:opscope-demo' {
  const payload: import('./types').Payload | null
  export default payload
}
