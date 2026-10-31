import metadata from '../package.json';
export default function AppVersion(){
 return <small className="text-secondary d-block text-center my-2">Gather &amp; Gift v{metadata.version}</small>;
}
