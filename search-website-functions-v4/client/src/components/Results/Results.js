import React from 'react';
import Result from './Result/Result';

import "./Results.css";

export default function Results(props) {

  let results = props.documents.map((result, index) => {
    return <Result 
        key={index} 
        document={result.document}
      />;
  });
  let filterDesc = props.filters.map(filter => filter.value).join(' ');
  console.log(filterDesc);
  let userSearchDesc = props.keywords.length > 0 ? 
                          `<h5>You searched for: <strong><u>${props.keywords}</u></strong></h5>`:
                          `<h2>${filterDesc} Parts</h2><hr/>`; 
  let beginDocNumber = Math.min(props.skip + 1, props.count);
  let endDocNumber = Math.min(props.skip + props.top, props.count);

  return (
    <div>
      {/* <div><</div> */}
      <div>
      <p className="results-info" dangerouslySetInnerHTML={{__html: userSearchDesc}}/>
        <p className="results-info">Showing {beginDocNumber}-{endDocNumber} of {props.count.toLocaleString()} results</p>
        <div className="row row-cols-md-4 results">
          {results}
        </div>
      </div>
    </div>
  );
};
