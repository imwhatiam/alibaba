import React from 'react';
import PropTypes from 'prop-types';
import { Button, Modal, ModalHeader, ModalBody, ModalFooter } from 'reactstrap';
import { gettext } from '../../utils/constants';


const propTypes = {
  toggle: PropTypes.func.isRequired,
  item: PropTypes.object.isRequired,
};

class PinganApproveStatusDialog extends React.Component {

  render() {
    return (
      <Modal isOpen={true} toggle={this.props.toggle}>
        <ModalHeader toggle={this.props.toggle}>{gettext('审核状态')}</ModalHeader>
        <ModalBody>
          <ul className="ml-2">
            {this.props.item.detailed_approve_status.map((item, idx) => {
              if (idx == 0) {
                return (
                  <li key={idx}> {item[1]}
                    <ul className="ml-2">
                      <li>命中信息：{this.props.item.breach_content}</li>
                      <li>策略类型：{this.props.item.policy_categories}</li>
                      <li>总计：{this.props.item.total_matches}</li>
                    </ul>
                  </li>
                )
              } else {
                return (
                  <li key={idx}>{item[1]}</li>
                )
              }
            })}
            {/* {this.props.item.detailed_approve_status} */}
          </ul>
        </ModalBody>
        <ModalFooter>
          <Button color="secondary" onClick={this.props.toggle}>{gettext('Close')}</Button>
        </ModalFooter>
      </Modal>
    );
  }
}

PinganApproveStatusDialog.propTypes = propTypes;

export default PinganApproveStatusDialog;
